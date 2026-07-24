from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Protocol

from .contracts import AuditEvent, JobState, MergeDecision, utc_now
from .github_adapter import DryRunMutationExecutor, GitHubAdapter, MutationCommand, MutationKind
from .store import JsonJobStore
from .validation import ValidationStatus


class MergerError(RuntimeError):
    pass


@dataclass(frozen=True)
class MergeFinding:
    code: str
    message: str
    blocking: bool = True


@dataclass(frozen=True)
class MergeReport:
    pull_request_number: int
    expected_head_sha: str
    base_branch: str
    merge_method: str
    allowed: bool
    findings: tuple[MergeFinding, ...] = field(default_factory=tuple)
    policy_version: int = 1


@dataclass(frozen=True)
class MergerRunResult:
    job_id: str
    state: JobState
    report: MergeReport
    decision: MergeDecision
    dry_run_operation_id: str


class MergerAgent(Protocol):
    def run(self, job_id: str, pull_request_number: int) -> MergerRunResult: ...


class DryRunMergerAgent:
    """Stateless Merger slice that persists policy decisions and performs no GitHub merge."""

    def __init__(
        self,
        store: JsonJobStore,
        github: GitHubAdapter,
        mutations: DryRunMutationExecutor,
        *,
        merge_method: str = "squash",
    ):
        self.store = store
        self.github = github
        self.mutations = mutations
        self.merge_method = merge_method

    @staticmethod
    def _operation(job_id: str, action: str) -> str:
        return f"{job_id}:merger:{action}"

    def _persist(self, job_id: str, operation_id: str, payload: dict, event_type: str) -> dict:
        existing = self.store.get_operation_result(operation_id)
        if existing is not None:
            return existing
        event = AuditEvent(
            event_id=f"{job_id}:{event_type}:{operation_id}",
            job_id=job_id,
            operation_id=operation_id,
            event_type=event_type,
            timestamp=utc_now(),
            details=payload,
        )
        return self.store.record_operation_result(job_id, operation_id, payload, event)

    def _transition(self, job_id: str, target: JobState, action: str):
        job = self.store.get(job_id)
        if job.state == target:
            return job
        return self.store.transition(job_id, target, self._operation(job_id, action))

    def _artifact(self, job_id: str, suffix: str) -> dict:
        result = self.store.get_operation_result(f"{job_id}:{suffix}")
        if result is None:
            raise MergerError(f"Missing required persisted artifact: {suffix}")
        return result

    def run(self, job_id: str, pull_request_number: int) -> MergerRunResult:
        job = self.store.get(job_id)
        if job.state in {JobState.BLOCKED, JobState.FAILED, JobState.CANCELLED, JobState.COMPLETED}:
            raise MergerError(f"Merger cannot run terminal job in state {job.state.value!r}")
        if job.state not in {JobState.APPROVED, JobState.MERGING}:
            raise MergerError(f"Merger does not own job state {job.state.value!r}")

        review_payload = self._artifact(job_id, "reviewer:result")
        validation_payload = self._artifact(job_id, "worker:validation")
        review_result = review_payload.get("review_result", {})
        reviewed_head_sha = str(review_payload.get("reviewed_head_sha") or "")
        validation_status = ValidationStatus(validation_payload["status"])

        pull_request = self.github.pull_request(job.repository, pull_request_number)
        checks = self.github.checks(job.repository, pull_request.head_sha)

        findings: list[MergeFinding] = []
        if not bool(review_result.get("approved")):
            findings.append(MergeFinding("review_not_approved", "Persisted review is not approved"))
        if not reviewed_head_sha:
            findings.append(MergeFinding("review_head_missing", "Persisted review is missing a reviewed head SHA"))
        elif reviewed_head_sha != pull_request.head_sha:
            findings.append(MergeFinding("stale_approval", "Reviewed head SHA differs from the current pull-request head"))
        if validation_status != ValidationStatus.PASSED:
            findings.append(MergeFinding("validation_failed", "Persisted validation did not pass"))
        if pull_request.state != "open":
            findings.append(MergeFinding("pr_not_open", "Pull request is not open"))
        if pull_request.draft:
            findings.append(MergeFinding("pr_is_draft", "Pull request is still a draft"))
        if pull_request.base_branch != job.repository.default_branch:
            findings.append(MergeFinding("base_branch_mismatch", "Pull request does not target the configured default branch"))
        if not checks.successful:
            findings.append(MergeFinding("checks_unsuccessful", "Required checks are not successful"))

        allowed = not any(finding.blocking for finding in findings)
        report = MergeReport(
            pull_request_number=pull_request.number,
            expected_head_sha=pull_request.head_sha,
            base_branch=pull_request.base_branch,
            merge_method=self.merge_method,
            allowed=allowed,
            findings=tuple(findings),
        )
        report_payload = {
            "report": {
                "pull_request_number": report.pull_request_number,
                "expected_head_sha": report.expected_head_sha,
                "base_branch": report.base_branch,
                "merge_method": report.merge_method,
                "allowed": report.allowed,
                "findings": [asdict(finding) for finding in report.findings],
                "policy_version": report.policy_version,
            }
        }
        self._persist(job_id, self._operation(job_id, "report"), report_payload, "merger.report.created")

        decision = MergeDecision(
            allowed=allowed,
            reason=(
                f"Dry-run merge allowed for PR #{pull_request.number}"
                if allowed
                else f"Dry-run merge blocked by {len(findings)} policy finding(s)"
            ),
        )
        self._persist(
            job_id,
            self._operation(job_id, "decision"),
            {"merge_decision": asdict(decision), **report_payload},
            "merger.decision.created",
        )

        command = MutationCommand(
            operation_id=self._operation(job_id, "github-merge"),
            kind=MutationKind.MERGE_PULL_REQUEST,
            repository=job.repository,
            payload={
                "pull_request_number": pull_request.number,
                "merge_method": self.merge_method,
                "expected_head_sha": pull_request.head_sha,
            },
        )
        if allowed:
            if self.store.get(job_id).state == JobState.APPROVED:
                self._transition(job_id, JobState.MERGING, "start")
            self.mutations.execute(job_id, command)
            self._persist(
                job_id,
                self._operation(job_id, "result"),
                {
                    "merge_decision": asdict(decision),
                    "pull_request_number": pull_request.number,
                    "expected_head_sha": pull_request.head_sha,
                    "merge_method": self.merge_method,
                },
                "merger.completed",
            )
            if self.store.get(job_id).state == JobState.MERGING:
                self._transition(job_id, JobState.COMPLETED, "complete")

        return MergerRunResult(
            job_id=job_id,
            state=self.store.get(job_id).state,
            report=report,
            decision=decision,
            dry_run_operation_id=command.operation_id,
        )
