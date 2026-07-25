from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Protocol

from .code_editing import CodeEditPlan, CodeEditingWorkerRunResult, GuardedCodeEditingWorker
from .contracts import AuditEvent, JobState, utc_now
from .store import JsonJobStore


class ProductionWorkerActivationError(RuntimeError):
    pass


class EmergencyStop(Protocol):
    def active(self) -> bool: ...


@dataclass(frozen=True)
class ProductionWorkerManifest:
    repository_allowlist: tuple[str, ...]
    path_allowlist: tuple[str, ...]
    command_allowlist: tuple[str, ...]
    mutation_allowlist: tuple[str, ...]
    required_token_scopes: tuple[str, ...]
    draft_pull_requests_only: bool = True
    reviewer_enabled: bool = False
    merger_enabled: bool = False
    always_on_scheduler_enabled: bool = False
    schema_version: int = 1

    def validate(self) -> None:
        required = {
            "repository_allowlist": self.repository_allowlist,
            "path_allowlist": self.path_allowlist,
            "command_allowlist": self.command_allowlist,
            "mutation_allowlist": self.mutation_allowlist,
            "required_token_scopes": self.required_token_scopes,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ProductionWorkerActivationError(
                f"Incomplete production Worker manifest: {', '.join(sorted(missing))}"
            )
        if self.draft_pull_requests_only is not True:
            raise ProductionWorkerActivationError("Production Worker requires draft pull requests only")
        if self.reviewer_enabled or self.merger_enabled or self.always_on_scheduler_enabled:
            raise ProductionWorkerActivationError(
                "Reviewer, Merger, and always-on scheduler must remain disabled"
            )

    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ProductionWorkerReport:
    job_id: str
    issue_number: int
    repository: str
    manifest_digest: str
    status: str
    workspace_id: str | None = None
    local_commit_sha: str | None = None
    pull_request_number: int | None = None
    validation_status: str | None = None
    unresolved_gates: tuple[str, ...] = field(
        default=(
            "production_reviewer_disabled",
            "production_merger_disabled",
            "always_on_scheduler_disabled",
        )
    )


class GuardedProductionWorkerRunner:
    """Runs exactly one explicitly selected production Worker job to a draft PR."""

    def __init__(
        self,
        store: JsonJobStore,
        worker: GuardedCodeEditingWorker,
        emergency_stop: EmergencyStop,
        *,
        manifest: ProductionWorkerManifest,
        enabled: bool = False,
    ):
        manifest.validate()
        self.store = store
        self.worker = worker
        self.emergency_stop = emergency_stop
        self.manifest = manifest
        self.enabled = enabled

    @staticmethod
    def _operation(job_id: str, action: str) -> str:
        return f"{job_id}:production-worker:{action}"

    def _persist(self, job_id: str, report: ProductionWorkerReport, event_type: str) -> dict:
        operation_id = self._operation(job_id, "report")
        existing = self.store.get_operation_result(operation_id)
        if existing is not None:
            return existing
        payload = asdict(report)
        event = AuditEvent(
            event_id=f"{job_id}:{event_type}:{operation_id}",
            job_id=job_id,
            operation_id=operation_id,
            event_type=event_type,
            timestamp=utc_now(),
            details=payload,
        )
        return self.store.record_operation_result(job_id, operation_id, payload, event)

    @staticmethod
    def _from_payload(payload: dict) -> ProductionWorkerReport:
        return ProductionWorkerReport(
            job_id=payload["job_id"],
            issue_number=payload["issue_number"],
            repository=payload["repository"],
            manifest_digest=payload["manifest_digest"],
            status=payload["status"],
            workspace_id=payload.get("workspace_id"),
            local_commit_sha=payload.get("local_commit_sha"),
            pull_request_number=payload.get("pull_request_number"),
            validation_status=payload.get("validation_status"),
            unresolved_gates=tuple(payload.get("unresolved_gates", ())),
        )

    def run_selected_issue(self, job_id: str, issue_number: int, plan: CodeEditPlan) -> ProductionWorkerReport:
        if not self.enabled:
            raise ProductionWorkerActivationError("Production Worker activation is disabled")
        if self.emergency_stop.active():
            raise ProductionWorkerActivationError("Emergency stop is active")

        existing = self.store.get_operation_result(self._operation(job_id, "report"))
        if existing is not None:
            return self._from_payload(existing)

        job = self.store.get(job_id)
        repository = f"{job.repository.owner}/{job.repository.name}"
        if repository not in self.manifest.repository_allowlist:
            raise ProductionWorkerActivationError(f"Repository is not allowlisted: {repository}")
        if job.request.issue_number != issue_number or plan.issue_number != issue_number:
            raise ProductionWorkerActivationError("Selected issue does not match job and plan")
        if job.state not in {JobState.CLAIMED, JobState.EXECUTING, JobState.VALIDATING}:
            raise ProductionWorkerActivationError(
                f"Production Worker cannot run job in state {job.state.value!r}"
            )
        if self.emergency_stop.active():
            raise ProductionWorkerActivationError("Emergency stop is active before Worker mutation")

        result: CodeEditingWorkerRunResult = self.worker.run(job_id, plan)
        if self.emergency_stop.active():
            raise ProductionWorkerActivationError("Emergency stop became active after Worker execution")
        if not result.validation.passed:
            raise ProductionWorkerActivationError("Validation did not pass")
        if result.worker_result.pull_request_number is None:
            raise ProductionWorkerActivationError("Worker did not create a draft pull request")

        report = ProductionWorkerReport(
            job_id=job_id,
            issue_number=issue_number,
            repository=repository,
            manifest_digest=self.manifest.digest(),
            status="draft_pr_created",
            workspace_id=result.workspace.workspace_id,
            local_commit_sha=result.workspace.commit_sha,
            pull_request_number=result.worker_result.pull_request_number,
            validation_status=result.validation.status.value,
        )
        self._persist(job_id, report, "production_worker.completed")
        return report
