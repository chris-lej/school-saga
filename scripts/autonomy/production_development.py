from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

from autonomy.code_editing import CodeEditPlan, GuardedCodeEditingWorker
from autonomy.contracts import AuditEvent, JobState, utc_now
from autonomy.rehearsal import EmergencyStop
from autonomy.scheduler import ProductionReadinessManifest
from autonomy.store import JsonJobStore


class ProductionDevelopmentStatus(str, Enum):
    READY = "ready"
    HALTED = "halted"
    FAILED = "failed"
    DRAFT_PR_CREATED = "draft_pr_created"


@dataclass(frozen=True)
class ProductionDevelopmentGate:
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class ProductionDevelopmentReport:
    job_id: str
    repository: str
    status: ProductionDevelopmentStatus
    gates: tuple[ProductionDevelopmentGate, ...] = field(default_factory=tuple)
    branch: str | None = None
    local_commit_sha: str | None = None
    pull_request_number: int | None = None
    unresolved_production_gates: tuple[str, ...] = (
        "production_review_disabled",
        "production_ready_transition_disabled",
        "production_merge_disabled",
        "always_on_scheduler_disabled",
    )


@dataclass(frozen=True)
class ProductionDevelopmentConfig:
    enabled: bool
    repository: str
    repository_root: str
    readiness_manifest: ProductionReadinessManifest
    allowed_branch_prefix: str = "autonomy/issue-"
    draft_pull_requests_only: bool = True
    reviews_enabled: bool = False
    merges_enabled: bool = False

    def validate(self) -> None:
        if not self.enabled:
            raise ValueError("production_development_guarded mode is disabled")
        if self.repository != "chris-lej/school-saga":
            raise ValueError("Production development is restricted to chris-lej/school-saga")
        if not Path(self.repository_root).is_dir():
            raise ValueError("Configured repository root does not exist")
        self.readiness_manifest.validate()
        if self.repository not in self.readiness_manifest.repository_allowlist:
            raise ValueError("Repository is absent from the readiness allowlist")
        required = {"claim_issue", "create_branch", "open_pull_request"}
        permitted = set(self.readiness_manifest.permitted_mutation_kinds)
        if not required.issubset(permitted):
            raise ValueError("Readiness manifest does not permit the required development mutations")
        if not self.draft_pull_requests_only:
            raise ValueError("Production development must remain draft-PR-only")
        if self.reviews_enabled or self.merges_enabled:
            raise ValueError("Production review and merge must remain disabled")
        if not self.allowed_branch_prefix:
            raise ValueError("allowed_branch_prefix cannot be empty")


class GuardedProductionDevelopmentRunner:
    """One-shot guarded production run that may create a validated draft PR only."""

    def __init__(
        self,
        store: JsonJobStore,
        worker: GuardedCodeEditingWorker,
        emergency_stop: EmergencyStop,
        config: ProductionDevelopmentConfig,
    ):
        config.validate()
        self.store = store
        self.worker = worker
        self.emergency_stop = emergency_stop
        self.config = config

    @staticmethod
    def _operation(job_id: str, action: str) -> str:
        return f"{job_id}:production-development:{action}"

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
    def _payload(report: ProductionDevelopmentReport) -> dict:
        payload = asdict(report)
        payload["status"] = report.status.value
        return payload

    @staticmethod
    def _from_payload(payload: dict) -> ProductionDevelopmentReport:
        return ProductionDevelopmentReport(
            job_id=payload["job_id"],
            repository=payload["repository"],
            status=ProductionDevelopmentStatus(payload["status"]),
            gates=tuple(ProductionDevelopmentGate(**gate) for gate in payload.get("gates", [])),
            branch=payload.get("branch"),
            local_commit_sha=payload.get("local_commit_sha"),
            pull_request_number=payload.get("pull_request_number"),
            unresolved_production_gates=tuple(payload.get("unresolved_production_gates", ())),
        )

    def run_to_draft_pr(self, job_id: str, plan: CodeEditPlan) -> ProductionDevelopmentReport:
        existing = self.store.get_operation_result(self._operation(job_id, "report"))
        if existing is not None:
            return self._from_payload(existing)

        job = self.store.get(job_id)
        repository = f"{job.repository.owner}/{job.repository.name}"
        gates = [
            ProductionDevelopmentGate("activation_enabled", self.config.enabled),
            ProductionDevelopmentGate("repository_identity", repository == self.config.repository, repository),
            ProductionDevelopmentGate(
                "job_state_eligible",
                job.state in {JobState.CLAIMED, JobState.EXECUTING, JobState.VALIDATING},
                job.state.value,
            ),
            ProductionDevelopmentGate(
                "branch_prefix",
                plan.branch.startswith(self.config.allowed_branch_prefix),
                plan.branch,
            ),
            ProductionDevelopmentGate("draft_pull_request_only", self.config.draft_pull_requests_only),
            ProductionDevelopmentGate("production_review_disabled", not self.config.reviews_enabled),
            ProductionDevelopmentGate("production_merge_disabled", not self.config.merges_enabled),
        ]
        if self.emergency_stop.active():
            report = ProductionDevelopmentReport(
                job_id=job_id,
                repository=repository,
                status=ProductionDevelopmentStatus.HALTED,
                gates=tuple(gates + [ProductionDevelopmentGate("emergency_stop", False, "active")]),
                branch=plan.branch,
            )
            self._persist(job_id, self._operation(job_id, "report"), self._payload(report), "production.development.halted")
            return report

        if not all(gate.passed for gate in gates):
            report = ProductionDevelopmentReport(
                job_id=job_id,
                repository=repository,
                status=ProductionDevelopmentStatus.FAILED,
                gates=tuple(gates),
                branch=plan.branch,
            )
            self._persist(job_id, self._operation(job_id, "report"), self._payload(report), "production.development.failed")
            return report

        try:
            result = self.worker.run(job_id, plan)
        except Exception as exc:
            report = ProductionDevelopmentReport(
                job_id=job_id,
                repository=repository,
                status=ProductionDevelopmentStatus.FAILED,
                gates=tuple(gates + [ProductionDevelopmentGate("guarded_worker", False, str(exc))]),
                branch=plan.branch,
            )
            self._persist(job_id, self._operation(job_id, "report"), self._payload(report), "production.development.failed")
            return report

        gates.extend(
            [
                ProductionDevelopmentGate("validation_passed", result.validation.passed, result.validation.status.value),
                ProductionDevelopmentGate("real_local_commit", bool(result.workspace.commit_sha), result.workspace.commit_sha),
                ProductionDevelopmentGate(
                    "draft_pull_request_created",
                    result.worker_result.pull_request_number is not None,
                    str(result.worker_result.pull_request_number or "missing"),
                ),
            ]
        )
        status = (
            ProductionDevelopmentStatus.DRAFT_PR_CREATED
            if all(gate.passed for gate in gates)
            else ProductionDevelopmentStatus.FAILED
        )
        report = ProductionDevelopmentReport(
            job_id=job_id,
            repository=repository,
            status=status,
            gates=tuple(gates),
            branch=plan.branch,
            local_commit_sha=result.workspace.commit_sha,
            pull_request_number=result.worker_result.pull_request_number,
        )
        self._persist(
            job_id,
            self._operation(job_id, "report"),
            self._payload(report),
            "production.development.completed" if status == ProductionDevelopmentStatus.DRAFT_PR_CREATED else "production.development.failed",
        )
        return report
