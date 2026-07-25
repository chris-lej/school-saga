from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Protocol

from .code_editing import CodeEditPlan, GuardedCodeEditingWorker
from .contracts import AuditEvent, JobState, utc_now
from .rehearsal import EmergencyStop
from .scheduler import ProductionReadinessManifest, SchedulerMode
from .store import JsonJobStore


class ProductionActivationError(RuntimeError):
    pass


class ActivationStatus(str, Enum):
    READY = "ready"
    HALTED = "halted"
    FAILED = "failed"
    DRAFT_PR_CREATED = "draft_pr_created"


@dataclass(frozen=True)
class ProductionDevelopmentConfig:
    mode: SchedulerMode
    repository: str
    manifest: ProductionReadinessManifest
    path_allowlist: tuple[str, ...]
    command_allowlist: tuple[str, ...]
    max_active_jobs: int = 1
    draft_pull_requests_only: bool = True
    review_enabled: bool = False
    merge_enabled: bool = False
    always_on_scheduler_enabled: bool = False

    def validate(self) -> None:
        if self.mode != SchedulerMode.PRODUCTION_GUARDED:
            raise ProductionActivationError("Production development requires production_guarded mode")
        self.manifest.validate()
        if self.repository not in self.manifest.repository_allowlist:
            raise ProductionActivationError("Production repository is not allowlisted")
        if not self.path_allowlist:
            raise ProductionActivationError("path_allowlist cannot be empty")
        if not self.command_allowlist:
            raise ProductionActivationError("command_allowlist cannot be empty")
        if self.max_active_jobs != 1:
            raise ProductionActivationError("Initial production development is limited to one active job")
        if not self.draft_pull_requests_only:
            raise ProductionActivationError("Production development permits draft pull requests only")
        if self.review_enabled or self.merge_enabled:
            raise ProductionActivationError("Production review and merge must remain disabled")
        if self.always_on_scheduler_enabled:
            raise ProductionActivationError("Always-on scheduling is not permitted in this activation slice")

    @property
    def digest(self) -> str:
        payload = {
            "mode": self.mode.value,
            "repository": self.repository,
            "manifest": asdict(self.manifest),
            "path_allowlist": self.path_allowlist,
            "command_allowlist": self.command_allowlist,
            "max_active_jobs": self.max_active_jobs,
            "draft_pull_requests_only": self.draft_pull_requests_only,
            "review_enabled": self.review_enabled,
            "merge_enabled": self.merge_enabled,
            "always_on_scheduler_enabled": self.always_on_scheduler_enabled,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ActivationGate:
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class ProductionActivationReport:
    activation_id: str
    job_id: str
    repository: str
    configuration_digest: str
    status: ActivationStatus
    gates: tuple[ActivationGate, ...] = field(default_factory=tuple)
    base_sha: str | None = None
    head_sha: str | None = None
    branch: str | None = None
    pull_request_number: int | None = None
    unresolved_capabilities: tuple[str, ...] = (
        "production_review_disabled",
        "production_merge_disabled",
        "always_on_scheduler_disabled",
    )


class ActivationPreflight(Protocol):
    def validate(self, config: ProductionDevelopmentConfig) -> tuple[ActivationGate, ...]: ...


class DefaultActivationPreflight:
    REQUIRED_MUTATIONS = {"claim_issue", "create_branch", "open_pull_request"}
    FORBIDDEN_MUTATIONS = {
        "submit_review",
        "mark_ready",
        "merge_pull_request",
        "auto_merge",
        "force_push",
        "delete_ref",
    }

    def validate(self, config: ProductionDevelopmentConfig) -> tuple[ActivationGate, ...]:
        config.validate()
        permitted = set(config.manifest.permitted_mutation_kinds)
        missing = sorted(self.REQUIRED_MUTATIONS - permitted)
        forbidden = sorted(self.FORBIDDEN_MUTATIONS & permitted)
        gates = [
            ActivationGate("configuration_complete", True, config.digest),
            ActivationGate("repository_allowlisted", True, config.repository),
            ActivationGate("single_active_job", config.max_active_jobs == 1, str(config.max_active_jobs)),
            ActivationGate("draft_pull_requests_only", config.draft_pull_requests_only),
            ActivationGate("production_review_disabled", not config.review_enabled),
            ActivationGate("production_merge_disabled", not config.merge_enabled),
            ActivationGate("always_on_scheduler_disabled", not config.always_on_scheduler_enabled),
            ActivationGate("required_mutations_enabled", not missing, ",".join(missing)),
            ActivationGate("forbidden_mutations_disabled", not forbidden, ",".join(forbidden)),
        ]
        if missing or forbidden:
            raise ProductionActivationError("Production mutation policy is incomplete or unsafe")
        return tuple(gates)


class ProductionDevelopmentController:
    """Operator-triggered, one-job production development controller."""

    def __init__(
        self,
        store: JsonJobStore,
        worker: GuardedCodeEditingWorker,
        emergency_stop: EmergencyStop,
        config: ProductionDevelopmentConfig,
        *,
        preflight: ActivationPreflight | None = None,
    ):
        self.store = store
        self.worker = worker
        self.emergency_stop = emergency_stop
        self.config = config
        self.preflight = preflight or DefaultActivationPreflight()

    @staticmethod
    def _operation(job_id: str, action: str) -> str:
        return f"{job_id}:production-activation:{action}"

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

    @staticmethod
    def _payload(report: ProductionActivationReport) -> dict:
        payload = asdict(report)
        payload["status"] = report.status.value
        return payload

    @staticmethod
    def _from_payload(payload: dict) -> ProductionActivationReport:
        return ProductionActivationReport(
            activation_id=payload["activation_id"],
            job_id=payload["job_id"],
            repository=payload["repository"],
            configuration_digest=payload["configuration_digest"],
            status=ActivationStatus(payload["status"]),
            gates=tuple(ActivationGate(**gate) for gate in payload.get("gates", ())),
            base_sha=payload.get("base_sha"),
            head_sha=payload.get("head_sha"),
            branch=payload.get("branch"),
            pull_request_number=payload.get("pull_request_number"),
            unresolved_capabilities=tuple(payload.get("unresolved_capabilities", ())),
        )

    def run_single_cycle(self, job_id: str, plan: CodeEditPlan) -> ProductionActivationReport:
        existing = self.store.get_operation_result(self._operation(job_id, "report"))
        if existing is not None:
            return self._from_payload(existing)

        job = self.store.get(job_id)
        repository = f"{job.repository.owner}/{job.repository.name}"
        if repository != self.config.repository:
            raise ProductionActivationError("Job repository does not match the activation profile")
        if job.state not in {JobState.CLAIMED, JobState.EXECUTING, JobState.VALIDATING}:
            raise ProductionActivationError(f"Job state is not eligible: {job.state.value}")

        gates = list(self.preflight.validate(self.config))
        activation_id = hashlib.sha256(
            f"{job_id}:{self.config.digest}:{plan.base_sha}:{plan.branch}".encode("utf-8")
        ).hexdigest()[:24]

        if self.emergency_stop.active():
            report = ProductionActivationReport(
                activation_id=activation_id,
                job_id=job_id,
                repository=repository,
                configuration_digest=self.config.digest,
                status=ActivationStatus.HALTED,
                gates=tuple(gates + [ActivationGate("emergency_stop", False, "active")]),
                base_sha=plan.base_sha,
                branch=plan.branch,
            )
            self._persist(job_id, self._operation(job_id, "report"), self._payload(report), "production_activation.halted")
            return report

        gates.append(ActivationGate("emergency_stop", True, "inactive"))
        try:
            result = self.worker.run(job_id, plan)
        except Exception as exc:
            report = ProductionActivationReport(
                activation_id=activation_id,
                job_id=job_id,
                repository=repository,
                configuration_digest=self.config.digest,
                status=ActivationStatus.FAILED,
                gates=tuple(gates + [ActivationGate("guarded_worker", False, str(exc))]),
                base_sha=plan.base_sha,
                branch=plan.branch,
            )
            self._persist(job_id, self._operation(job_id, "report"), self._payload(report), "production_activation.failed")
            return report

        gates.extend(
            [
                ActivationGate("validation_passed", result.validation.passed, result.validation.status.value),
                ActivationGate("real_commit_created", bool(result.workspace.commit_sha), result.workspace.commit_sha),
                ActivationGate("draft_pull_request_created", result.worker_result.pull_request_number is not None),
            ]
        )
        passed = all(gate.passed for gate in gates)
        report = ProductionActivationReport(
            activation_id=activation_id,
            job_id=job_id,
            repository=repository,
            configuration_digest=self.config.digest,
            status=ActivationStatus.DRAFT_PR_CREATED if passed else ActivationStatus.FAILED,
            gates=tuple(gates),
            base_sha=plan.base_sha,
            head_sha=result.workspace.commit_sha,
            branch=plan.branch,
            pull_request_number=result.worker_result.pull_request_number,
        )
        self._persist(
            job_id,
            self._operation(job_id, "report"),
            self._payload(report),
            "production_activation.completed" if passed else "production_activation.failed",
        )
        return report
