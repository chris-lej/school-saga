from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Protocol

from .code_editing import CodeEditPlan, CodeEditingWorkerRunResult, GuardedCodeEditingWorker
from .contracts import AuditEvent, JobState, utc_now
from .store import JsonJobStore


class RehearsalStatus(str, Enum):
    READY = "ready"
    HALTED = "halted"
    FAILED = "failed"
    DRAFT_PR_CREATED = "draft_pr_created"


@dataclass(frozen=True)
class RehearsalGate:
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class RehearsalReport:
    job_id: str
    repository: str
    status: RehearsalStatus
    gates: tuple[RehearsalGate, ...] = field(default_factory=tuple)
    local_commit_sha: str | None = None
    pull_request_number: int | None = None
    unresolved_production_gates: tuple[str, ...] = (
        "production_review_disabled",
        "production_merge_disabled",
        "always_on_scheduler_disabled",
    )


class EmergencyStop(Protocol):
    def active(self) -> bool: ...


class StaticEmergencyStop:
    def __init__(self, active: bool = False):
        self._active = active

    def active(self) -> bool:
        return self._active


class RehearsalError(RuntimeError):
    pass


class GuardedRehearsalRunner:
    """Runs one isolated issue-to-draft-PR rehearsal using persisted operations."""

    def __init__(
        self,
        store: JsonJobStore,
        worker: GuardedCodeEditingWorker,
        emergency_stop: EmergencyStop,
        *,
        isolated_repository_allowlist: tuple[str, ...],
    ):
        if not isolated_repository_allowlist:
            raise ValueError("isolated_repository_allowlist cannot be empty")
        self.store = store
        self.worker = worker
        self.emergency_stop = emergency_stop
        self.isolated_repository_allowlist = isolated_repository_allowlist

    @staticmethod
    def _operation(job_id: str, action: str) -> str:
        return f"{job_id}:rehearsal:{action}"

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

    def _halted_report(self, job_id: str, repository: str) -> RehearsalReport:
        report = RehearsalReport(
            job_id=job_id,
            repository=repository,
            status=RehearsalStatus.HALTED,
            gates=(RehearsalGate("emergency_stop", False, "Emergency stop is active"),),
        )
        self._persist(
            job_id,
            self._operation(job_id, "halted"),
            self._report_payload(report),
            "rehearsal.halted",
        )
        return report

    @staticmethod
    def _report_payload(report: RehearsalReport) -> dict:
        payload = asdict(report)
        payload["status"] = report.status.value
        return payload

    def run_to_draft_pr(self, job_id: str, plan: CodeEditPlan) -> RehearsalReport:
        job = self.store.get(job_id)
        repository = f"{job.repository.owner}/{job.repository.name}"
        if repository not in self.isolated_repository_allowlist:
            raise RehearsalError(f"Repository is not allowlisted for rehearsal: {repository}")
        if job.state not in {JobState.CLAIMED, JobState.EXECUTING, JobState.VALIDATING}:
            raise RehearsalError(f"Rehearsal cannot run job in state {job.state.value!r}")
        if self.emergency_stop.active():
            return self._halted_report(job_id, repository)

        existing = self.store.get_operation_result(self._operation(job_id, "report"))
        if existing is not None:
            return self._report_from_payload(existing)

        gates = [
            RehearsalGate("isolated_repository_allowlisted", True, repository),
            RehearsalGate("draft_pull_request_only", True),
            RehearsalGate("production_review_disabled", True),
            RehearsalGate("production_merge_disabled", True),
        ]

        if self.emergency_stop.active():
            return self._halted_report(job_id, repository)

        try:
            result: CodeEditingWorkerRunResult = self.worker.run(job_id, plan)
        except Exception as exc:
            report = RehearsalReport(
                job_id=job_id,
                repository=repository,
                status=RehearsalStatus.FAILED,
                gates=tuple(gates + [RehearsalGate("guarded_worker", False, str(exc))]),
            )
            self._persist(
                job_id,
                self._operation(job_id, "report"),
                self._report_payload(report),
                "rehearsal.failed",
            )
            return report

        gates.extend(
            [
                RehearsalGate("validation_passed", result.validation.passed, result.validation.status.value),
                RehearsalGate("real_local_commit", bool(result.workspace.commit_sha), result.workspace.commit_sha),
                RehearsalGate(
                    "draft_pull_request_created",
                    result.worker_result.pull_request_number is not None,
                    str(result.worker_result.pull_request_number or "missing"),
                ),
            ]
        )
        status = (
            RehearsalStatus.DRAFT_PR_CREATED
            if all(gate.passed for gate in gates)
            else RehearsalStatus.FAILED
        )
        report = RehearsalReport(
            job_id=job_id,
            repository=repository,
            status=status,
            gates=tuple(gates),
            local_commit_sha=result.workspace.commit_sha,
            pull_request_number=result.worker_result.pull_request_number,
        )
        self._persist(
            job_id,
            self._operation(job_id, "report"),
            self._report_payload(report),
            "rehearsal.completed" if status == RehearsalStatus.DRAFT_PR_CREATED else "rehearsal.failed",
        )
        return report

    @staticmethod
    def _report_from_payload(payload: dict) -> RehearsalReport:
        return RehearsalReport(
            job_id=payload["job_id"],
            repository=payload["repository"],
            status=RehearsalStatus(payload["status"]),
            gates=tuple(RehearsalGate(**gate) for gate in payload.get("gates", [])),
            local_commit_sha=payload.get("local_commit_sha"),
            pull_request_number=payload.get("pull_request_number"),
            unresolved_production_gates=tuple(payload.get("unresolved_production_gates", ())),
        )
