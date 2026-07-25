from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol

from .code_editing import CodeEditPlan, CodeEditingWorkerRunResult, GuardedCodeEditingWorker
from .contracts import AuditEvent, utc_now
from .store import JsonJobStore


class ActivationStatus(str, Enum):
    READY = "ready"
    HALTED = "halted"
    FAILED = "failed"
    DRAFT_PR_CREATED = "draft_pr_created"


@dataclass(frozen=True)
class ActivationGate:
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class ProductionActivationConfig:
    repository: str
    repository_root: str
    expected_default_branch_sha: str
    issue_label_allowlist: tuple[str, ...]
    path_allowlist: tuple[str, ...]
    validation_command_allowlist: tuple[str, ...]
    mutation_allowlist: tuple[str, ...]
    token_source: str
    rollback_procedure: str
    emergency_stop_source: str
    required_checks: tuple[str, ...]
    production_development_enabled: bool = False
    reviews_enabled: bool = False
    ready_for_review_enabled: bool = False
    merges_enabled: bool = False
    unattended_scheduler_enabled: bool = False

    def validate(self) -> None:
        if not self.production_development_enabled:
            raise ValueError("Production development mode is disabled")
        if self.reviews_enabled or self.ready_for_review_enabled or self.merges_enabled:
            raise ValueError("Review, ready-for-review, and merge must remain disabled")
        if self.unattended_scheduler_enabled:
            raise ValueError("Unattended scheduler must remain disabled")
        required = {
            "repository": self.repository,
            "repository_root": self.repository_root,
            "expected_default_branch_sha": self.expected_default_branch_sha,
            "token_source": self.token_source,
            "rollback_procedure": self.rollback_procedure,
            "emergency_stop_source": self.emergency_stop_source,
        }
        missing = sorted(name for name, value in required.items() if not value)
        if missing:
            raise ValueError(f"Incomplete activation configuration: {', '.join(missing)}")
        if not self.issue_label_allowlist:
            raise ValueError("issue_label_allowlist cannot be empty")
        if not self.path_allowlist:
            raise ValueError("path_allowlist cannot be empty")
        if not self.validation_command_allowlist:
            raise ValueError("validation_command_allowlist cannot be empty")
        if not self.mutation_allowlist:
            raise ValueError("mutation_allowlist cannot be empty")
        if not self.required_checks:
            raise ValueError("required_checks cannot be empty")


@dataclass(frozen=True)
class ProductionActivationReport:
    job_id: str
    repository: str
    status: ActivationStatus
    gates: tuple[ActivationGate, ...] = field(default_factory=tuple)
    branch: str | None = None
    commit_sha: str | None = None
    pull_request_number: int | None = None
    disabled_capabilities: tuple[str, ...] = (
        "production_review",
        "ready_for_review",
        "production_merge",
        "unattended_scheduler",
    )


class EmergencyStop(Protocol):
    def active(self) -> bool: ...


class ProductionPreflight(Protocol):
    def run(self, config: ProductionActivationConfig) -> tuple[ActivationGate, ...]: ...


class StaticProductionPreflight:
    """Deterministic preflight used by tests and trusted runtime wiring."""

    def __init__(self, gates: tuple[ActivationGate, ...] = ()):
        self.gates = gates

    def run(self, config: ProductionActivationConfig) -> tuple[ActivationGate, ...]:
        config.validate()
        root = Path(config.repository_root).resolve()
        defaults = (
            ActivationGate("repository_root_exists", root.is_dir(), str(root)),
            ActivationGate("review_disabled", not config.reviews_enabled),
            ActivationGate("ready_for_review_disabled", not config.ready_for_review_enabled),
            ActivationGate("merge_disabled", not config.merges_enabled),
            ActivationGate("unattended_scheduler_disabled", not config.unattended_scheduler_enabled),
        )
        return defaults + self.gates


class ProductionActivationError(RuntimeError):
    pass


class GuardedProductionActivation:
    """Runs one manually selected issue through a guarded production draft PR."""

    def __init__(
        self,
        store: JsonJobStore,
        worker: GuardedCodeEditingWorker,
        preflight: ProductionPreflight,
        emergency_stop: EmergencyStop,
        config: ProductionActivationConfig,
    ):
        config.validate()
        self.store = store
        self.worker = worker
        self.preflight = preflight
        self.emergency_stop = emergency_stop
        self.config = config

    @staticmethod
    def _operation(job_id: str, action: str) -> str:
        return f"{job_id}:production-activation:{action}"

    @staticmethod
    def _payload(report: ProductionActivationReport) -> dict:
        payload = asdict(report)
        payload["status"] = report.status.value
        return payload

    def _persist(self, report: ProductionActivationReport, event_type: str) -> ProductionActivationReport:
        operation_id = self._operation(report.job_id, "report")
        existing = self.store.get_operation_result(operation_id)
        if existing is not None:
            return self._from_payload(existing)
        event = AuditEvent(
            event_id=f"{report.job_id}:{event_type}:{operation_id}",
            job_id=report.job_id,
            operation_id=operation_id,
            event_type=event_type,
            timestamp=utc_now(),
            details=self._payload(report),
        )
        self.store.record_operation_result(report.job_id, operation_id, self._payload(report), event)
        return report

    def run_one(self, job_id: str, plan: CodeEditPlan) -> ProductionActivationReport:
        existing = self.store.get_operation_result(self._operation(job_id, "report"))
        if existing is not None:
            return self._from_payload(existing)

        job = self.store.get(job_id)
        repository = f"{job.repository.owner}/{job.repository.name}"
        if repository != self.config.repository:
            raise ProductionActivationError(f"Activation repository mismatch: {repository}")
        if self.emergency_stop.active():
            return self._persist(
                ProductionActivationReport(
                    job_id=job_id,
                    repository=repository,
                    status=ActivationStatus.HALTED,
                    gates=(ActivationGate("emergency_stop", False, "Emergency stop is active"),),
                ),
                "production_activation.halted",
            )

        gates = list(self.preflight.run(self.config))
        if not all(gate.passed for gate in gates):
            return self._persist(
                ProductionActivationReport(
                    job_id=job_id,
                    repository=repository,
                    status=ActivationStatus.FAILED,
                    gates=tuple(gates),
                ),
                "production_activation.failed",
            )

        if self.emergency_stop.active():
            gates.append(ActivationGate("emergency_stop", False, "Emergency stop activated after preflight"))
            return self._persist(
                ProductionActivationReport(
                    job_id=job_id,
                    repository=repository,
                    status=ActivationStatus.HALTED,
                    gates=tuple(gates),
                ),
                "production_activation.halted",
            )

        try:
            result: CodeEditingWorkerRunResult = self.worker.run(job_id, plan)
        except Exception as exc:
            gates.append(ActivationGate("guarded_worker", False, str(exc)))
            return self._persist(
                ProductionActivationReport(
                    job_id=job_id,
                    repository=repository,
                    status=ActivationStatus.FAILED,
                    gates=tuple(gates),
                ),
                "production_activation.failed",
            )

        gates.extend(
            (
                ActivationGate("validation_passed", result.validation.passed, result.validation.status.value),
                ActivationGate("real_commit_created", bool(result.workspace.commit_sha), result.workspace.commit_sha),
                ActivationGate(
                    "draft_pull_request_created",
                    result.worker_result.pull_request_number is not None,
                    str(result.worker_result.pull_request_number or "missing"),
                ),
            )
        )
        passed = all(gate.passed for gate in gates)
        report = ProductionActivationReport(
            job_id=job_id,
            repository=repository,
            status=ActivationStatus.DRAFT_PR_CREATED if passed else ActivationStatus.FAILED,
            gates=tuple(gates),
            branch=result.workspace.branch,
            commit_sha=result.workspace.commit_sha,
            pull_request_number=result.worker_result.pull_request_number,
        )
        return self._persist(
            report,
            "production_activation.completed" if passed else "production_activation.failed",
        )

    @staticmethod
    def _from_payload(payload: dict) -> ProductionActivationReport:
        return ProductionActivationReport(
            job_id=payload["job_id"],
            repository=payload["repository"],
            status=ActivationStatus(payload["status"]),
            gates=tuple(ActivationGate(**gate) for gate in payload.get("gates", ())),
            branch=payload.get("branch"),
            commit_sha=payload.get("commit_sha"),
            pull_request_number=payload.get("pull_request_number"),
            disabled_capabilities=tuple(payload.get("disabled_capabilities", ())),
        )
