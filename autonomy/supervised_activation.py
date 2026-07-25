from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from .readiness import ProductionReadinessGate, ReadinessConfig, SignedReadinessReport


class SupervisedActivationStatus(str, Enum):
    PREFLIGHT_ONLY = "preflight_only"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    HALTED = "halted"


@dataclass(frozen=True)
class SupervisedActivationConfig:
    enabled: bool = False
    live_execution_confirmed: bool = False
    selected_issue: int | None = None
    dry_run: bool = True
    one_active_job: bool = True
    unattended_scheduler_enabled: bool = False

    def validate(self) -> None:
        if not self.enabled:
            raise ValueError("Supervised activation is disabled")
        if self.selected_issue is None or self.selected_issue < 1:
            raise ValueError("Exactly one selected issue is required")
        if not self.one_active_job:
            raise ValueError("Exactly one active job is required")
        if self.unattended_scheduler_enabled:
            raise ValueError("Unattended scheduling remains disabled")
        if not self.dry_run and not self.live_execution_confirmed:
            raise ValueError("Live execution requires explicit confirmation")


class EmergencyStop(Protocol):
    def active(self) -> bool: ...


class ActiveJobProbe(Protocol):
    def has_active_job(self) -> bool: ...


class ProductionRuntime(Protocol):
    def run_selected_issue(self, issue_number: int) -> dict: ...


@dataclass(frozen=True)
class SupervisedActivationReport:
    status: SupervisedActivationStatus
    issue_number: int
    readiness_signature: str
    configuration_digest: str
    operations: tuple[str, ...] = field(default_factory=tuple)
    result: dict = field(default_factory=dict)
    detail: str = ""


class SupervisedProductionActivation:
    """Verifies signed readiness before one operator-triggered production cycle."""

    def __init__(
        self,
        readiness_gate: ProductionReadinessGate,
        emergency_stop: EmergencyStop,
        active_job_probe: ActiveJobProbe,
        runtime: ProductionRuntime,
    ):
        self.readiness_gate = readiness_gate
        self.emergency_stop = emergency_stop
        self.active_job_probe = active_job_probe
        self.runtime = runtime

    def run(
        self,
        config: SupervisedActivationConfig,
        readiness_report: SignedReadinessReport,
        readiness_config: ReadinessConfig,
    ) -> SupervisedActivationReport:
        config.validate()
        issue_number = int(config.selected_issue)

        if self.emergency_stop.active():
            return SupervisedActivationReport(
                SupervisedActivationStatus.HALTED,
                issue_number,
                readiness_report.signature,
                readiness_report.configuration_digest,
                detail="Emergency stop active",
            )

        self.readiness_gate.verify(readiness_report, readiness_config)

        if self.active_job_probe.has_active_job():
            return SupervisedActivationReport(
                SupervisedActivationStatus.BLOCKED,
                issue_number,
                readiness_report.signature,
                readiness_report.configuration_digest,
                detail="Another production job is active",
            )

        if config.dry_run:
            return SupervisedActivationReport(
                SupervisedActivationStatus.PREFLIGHT_ONLY,
                issue_number,
                readiness_report.signature,
                readiness_report.configuration_digest,
                operations=("readiness.verify", "active_job.verify", "issue.select"),
            )

        if self.emergency_stop.active():
            return SupervisedActivationReport(
                SupervisedActivationStatus.HALTED,
                issue_number,
                readiness_report.signature,
                readiness_report.configuration_digest,
                detail="Emergency stop active before production runtime",
            )

        result = self.runtime.run_selected_issue(issue_number)
        operations = tuple(result.get("operation_ids", ()))
        return SupervisedActivationReport(
            SupervisedActivationStatus.COMPLETED,
            issue_number,
            readiness_report.signature,
            readiness_report.configuration_digest,
            operations=operations,
            result=result,
        )
