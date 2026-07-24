from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Protocol

from .contracts import AuditEvent, JobState, WorkerResult, utc_now
from .github_adapter import (
    DryRunMutationExecutor,
    GitHubAdapter,
    MutationCommand,
    MutationKind,
)
from .store import JsonJobStore
from .validation import ValidationRunResult, ValidationService


class WorkerError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkPlan:
    issue_number: int
    title: str
    acceptance_items: tuple[str, ...]
    branch: str
    summary: str
    schema_version: int = 1


@dataclass(frozen=True)
class WorkerRunResult:
    job_id: str
    state: JobState
    plan: WorkPlan
    worker_result: WorkerResult
    validation: ValidationRunResult
    dry_run_operations: tuple[str, ...] = field(default_factory=tuple)


class WorkerAgent(Protocol):
    def run(self, job_id: str) -> WorkerRunResult: ...


class DryRunWorkerAgent:
    """Stateless Worker slice that persists every decision and performs no GitHub writes."""

    def __init__(
        self,
        store: JsonJobStore,
        github: GitHubAdapter,
        mutations: DryRunMutationExecutor,
        validation: ValidationService,
    ):
        self.store = store
        self.github = github
        self.mutations = mutations
        self.validation = validation

    @staticmethod
    def _operation(job_id: str, action: str) -> str:
        return f"{job_id}:worker:{action}"

    @staticmethod
    def _acceptance_items(body: str) -> tuple[str, ...]:
        items = []
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("- [ ]"):
                item = stripped[5:].strip()
                if item:
                    items.append(item)
        return tuple(items)

    def _persist_artifact(self, job_id: str, operation_id: str, result: dict, event_type: str) -> dict:
        existing = self.store.get_operation_result(operation_id)
        if existing is not None:
            return existing
        event = AuditEvent(
            event_id=f"{job_id}:{event_type}:{operation_id}",
            job_id=job_id,
            operation_id=operation_id,
            event_type=event_type,
            timestamp=utc_now(),
            details=result,
        )
        return self.store.record_operation_result(job_id, operation_id, result, event)

    def _transition(self, job_id: str, target: JobState, action: str):
        job = self.store.get(job_id)
        if job.state == target:
            return job
        return self.store.transition(job_id, target, self._operation(job_id, action))

    def run(self, job_id: str) -> WorkerRunResult:
        job = self.store.get(job_id)
        if job.state in {JobState.BLOCKED, JobState.FAILED, JobState.CANCELLED, JobState.COMPLETED}:
            raise WorkerError(f"Worker cannot run terminal job in state {job.state.value!r}")
        if job.state not in {JobState.QUEUED, JobState.CLAIMED, JobState.EXECUTING, JobState.VALIDATING}:
            raise WorkerError(f"Worker does not own job state {job.state.value!r}")

        issue = self.github.issue(job.repository, job.request.issue_number)
        eligible = issue.state == "open" and "state:ready" in issue.labels
        if not eligible:
            if job.state == JobState.QUEUED:
                self._transition(job_id, JobState.CLAIMED, "claim-ineligible")
            job = self.store.get(job_id)
            if job.state in {JobState.CLAIMED, JobState.EXECUTING, JobState.VALIDATING}:
                self.store.transition(job_id, JobState.BLOCKED, self._operation(job_id, "block-ineligible"))
            self._persist_artifact(
                job_id,
                self._operation(job_id, "eligibility-result"),
                {"eligible": False, "issue_state": issue.state, "labels": list(issue.labels)},
                "worker.blocked",
            )
            raise WorkerError("Issue is not open and marked state:ready")

        if job.state == JobState.QUEUED:
            self._transition(job_id, JobState.CLAIMED, "claim")
        job = self.store.get(job_id)
        if job.state == JobState.CLAIMED:
            self._transition(job_id, JobState.EXECUTING, "execute")

        branch = f"autonomy/issue-{issue.number}"
        plan = WorkPlan(
            issue_number=issue.number,
            title=issue.title,
            acceptance_items=self._acceptance_items(issue.body),
            branch=branch,
            summary=f"Dry-run plan for issue #{issue.number}: {issue.title}",
        )
        plan_payload = asdict(plan)
        self._persist_artifact(
            job_id,
            self._operation(job_id, "plan"),
            plan_payload,
            "worker.plan.created",
        )

        commands = (
            MutationCommand(
                operation_id=self._operation(job_id, "github-claim"),
                kind=MutationKind.CLAIM_ISSUE,
                repository=job.repository,
                payload={"issue_number": issue.number},
            ),
            MutationCommand(
                operation_id=self._operation(job_id, "github-branch"),
                kind=MutationKind.CREATE_BRANCH,
                repository=job.repository,
                payload={"branch": branch, "base": job.repository.default_branch},
            ),
            MutationCommand(
                operation_id=self._operation(job_id, "github-pr"),
                kind=MutationKind.OPEN_PULL_REQUEST,
                repository=job.repository,
                payload={"issue_number": issue.number, "head": branch, "base": job.repository.default_branch},
            ),
        )
        for command in commands:
            self.mutations.execute(job_id, command)

        job = self.store.get(job_id)
        if job.state == JobState.EXECUTING:
            self._transition(job_id, JobState.VALIDATING, "validate")
        validation = self.validation.validate(job_id, self._operation(job_id, "validation"))

        worker_result = WorkerResult(
            branch=branch,
            summary=f"Dry-run Worker planned issue #{issue.number}; validation={validation.status.value}",
        )
        self._persist_artifact(
            job_id,
            self._operation(job_id, "result"),
            {
                "worker_result": asdict(worker_result),
                "plan": plan_payload,
                "validation_operation_id": validation.operation_id,
                "validation_status": validation.status.value,
            },
            "worker.completed",
        )
        return WorkerRunResult(
            job_id=job_id,
            state=self.store.get(job_id).state,
            plan=plan,
            worker_result=worker_result,
            validation=validation,
            dry_run_operations=tuple(command.operation_id for command in commands),
        )
