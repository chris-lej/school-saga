from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Protocol

from .contracts import AuditEvent, JobState, ReviewResult, utc_now
from .github_adapter import (
    DryRunMutationExecutor,
    GitHubAdapter,
    MutationCommand,
    MutationKind,
)
from .store import JsonJobStore
from .validation import ValidationStatus


class ReviewerError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReviewFinding:
    code: str
    message: str
    blocking: bool = True


@dataclass(frozen=True)
class ReviewReport:
    pull_request_number: int
    reviewed_head_sha: str
    approved: bool
    findings: tuple[ReviewFinding, ...] = field(default_factory=tuple)
    policy_version: int = 1


@dataclass(frozen=True)
class ReviewerRunResult:
    job_id: str
    state: JobState
    report: ReviewReport
    review_result: ReviewResult
    dry_run_operation_id: str


class ReviewerAgent(Protocol):
    def run(self, job_id: str, pull_request_number: int) -> ReviewerRunResult: ...


class DryRunReviewerAgent:
    """Stateless Reviewer slice that persists policy decisions and performs no GitHub writes."""

    def __init__(
        self,
        store: JsonJobStore,
        github: GitHubAdapter,
        mutations: DryRunMutationExecutor,
    ):
        self.store = store
        self.github = github
        self.mutations = mutations

    @staticmethod
    def _operation(job_id: str, action: str) -> str:
        return f"{job_id}:reviewer:{action}"

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
            raise ReviewerError(f"Missing required persisted artifact: {suffix}")
        return result

    def run(self, job_id: str, pull_request_number: int) -> ReviewerRunResult:
        job = self.store.get(job_id)
        if job.state in {JobState.BLOCKED, JobState.FAILED, JobState.CANCELLED, JobState.COMPLETED}:
            raise ReviewerError(f"Reviewer cannot run terminal job in state {job.state.value!r}")
        if job.state not in {JobState.VALIDATING, JobState.REVIEWING, JobState.APPROVED}:
            raise ReviewerError(f"Reviewer does not own job state {job.state.value!r}")

        worker_payload = self._artifact(job_id, "worker:result")
        validation_payload = self._artifact(job_id, "worker:validation")
        validation_status = ValidationStatus(validation_payload["status"])

        pull_request = self.github.pull_request(job.repository, pull_request_number)
        checks = self.github.checks(job.repository, pull_request.head_sha)

        findings: list[ReviewFinding] = []
        if validation_status != ValidationStatus.PASSED:
            findings.append(ReviewFinding("validation_failed", "Persisted validation did not pass"))
        if pull_request.state != "open":
            findings.append(ReviewFinding("pr_not_open", "Pull request is not open"))
        if pull_request.draft:
            findings.append(ReviewFinding("pr_is_draft", "Pull request is still a draft"))
        if not checks.successful:
            findings.append(ReviewFinding("checks_unsuccessful", "Required checks are not successful"))

        expected_sha = worker_payload.get("worker_result", {}).get("commit_sha")
        if expected_sha and expected_sha != pull_request.head_sha:
            findings.append(ReviewFinding("stale_head", "Pull request head differs from the Worker result"))

        approved = not any(finding.blocking for finding in findings)
        report = ReviewReport(
            pull_request_number=pull_request.number,
            reviewed_head_sha=pull_request.head_sha,
            approved=approved,
            findings=tuple(findings),
        )

        if job.state == JobState.VALIDATING:
            self._transition(job_id, JobState.REVIEWING, "start")

        report_payload = {
            "report": {
                "pull_request_number": report.pull_request_number,
                "reviewed_head_sha": report.reviewed_head_sha,
                "approved": report.approved,
                "findings": [asdict(finding) for finding in report.findings],
                "policy_version": report.policy_version,
            }
        }
        self._persist(
            job_id,
            self._operation(job_id, "report"),
            report_payload,
            "reviewer.report.created",
        )

        command = MutationCommand(
            operation_id=self._operation(job_id, "github-review"),
            kind=MutationKind.SUBMIT_REVIEW,
            repository=job.repository,
            payload={
                "pull_request_number": pull_request.number,
                "event": "APPROVE" if approved else "REQUEST_CHANGES",
                "reviewed_head_sha": pull_request.head_sha,
            },
        )
        self.mutations.execute(job_id, command)

        review_result = ReviewResult(
            approved=approved,
            summary=(
                f"Dry-run Reviewer approved PR #{pull_request.number}"
                if approved
                else f"Dry-run Reviewer found {len(findings)} blocking issue(s) on PR #{pull_request.number}"
            ),
        )
        self._persist(
            job_id,
            self._operation(job_id, "result"),
            {
                "review_result": asdict(review_result),
                "reviewed_head_sha": pull_request.head_sha,
                "findings": [asdict(finding) for finding in findings],
            },
            "reviewer.completed",
        )

        if approved and self.store.get(job_id).state == JobState.REVIEWING:
            self._transition(job_id, JobState.APPROVED, "approve")

        return ReviewerRunResult(
            job_id=job_id,
            state=self.store.get(job_id).state,
            report=report,
            review_result=review_result,
            dry_run_operation_id=command.operation_id,
        )
