from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class DeploymentMode(str, Enum):
    DISABLED = "disabled"
    OBSERVE_ONLY = "observe_only"
    SINGLE_CYCLE = "single_cycle"
    ALWAYS_ON = "always_on"


class SchedulerState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    DRAINING = "draining"
    HALTED = "halted"
    FAILED = "failed"


@dataclass(frozen=True)
class UnattendedSchedulerConfig:
    mode: DeploymentMode = DeploymentMode.DISABLED
    max_cycles_per_run: int = 1
    one_active_issue: bool = True
    lease_owner: str = ""
    retry_backoff_seconds: int = 60

    def validate(self) -> None:
        if self.mode == DeploymentMode.DISABLED:
            raise ValueError("Unattended scheduler is disabled")
        if self.max_cycles_per_run < 1:
            raise ValueError("max_cycles_per_run must be at least one")
        if not self.one_active_issue:
            raise ValueError("Exactly one active issue is required")
        if not self.lease_owner:
            raise ValueError("lease_owner is required")
        if self.retry_backoff_seconds < 1:
            raise ValueError("retry_backoff_seconds must be positive")


class ReadinessVerifier(Protocol):
    def verify(self) -> str: ...


class EmergencyStop(Protocol):
    def active(self) -> bool: ...


class LeaseStore(Protocol):
    def acquire(self, owner: str) -> bool: ...
    def release(self, owner: str) -> None: ...
    def heartbeat(self, owner: str) -> None: ...


class CycleRuntime(Protocol):
    def run_cycle(self) -> dict: ...


@dataclass
class SchedulerControl:
    paused: bool = False
    draining: bool = False
    shutdown_requested: bool = False

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False
        self.draining = False

    def drain(self) -> None:
        self.draining = True

    def shutdown(self) -> None:
        self.shutdown_requested = True


@dataclass(frozen=True)
class SchedulerCycleRecord:
    cycle_number: int
    status: str
    issue_number: int | None = None
    detail: str = ""
    operation_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SchedulerHealth:
    state: SchedulerState
    readiness_reference: str = ""
    active_issue: int | None = None
    last_successful_cycle: int | None = None
    failed_cycles: int = 0
    quarantined_issues: tuple[int, ...] = field(default_factory=tuple)
    cycles: tuple[SchedulerCycleRecord, ...] = field(default_factory=tuple)


class BoundedUnattendedScheduler:
    """Runs guarded production cycles behind readiness, lease, and stop controls."""

    def __init__(
        self,
        readiness: ReadinessVerifier,
        emergency_stop: EmergencyStop,
        leases: LeaseStore,
        runtime: CycleRuntime,
        control: SchedulerControl,
        config: UnattendedSchedulerConfig,
    ):
        self.readiness = readiness
        self.emergency_stop = emergency_stop
        self.leases = leases
        self.runtime = runtime
        self.control = control
        self.config = config

    def run(self) -> SchedulerHealth:
        self.config.validate()
        readiness_reference = self.readiness.verify()
        if self.emergency_stop.active():
            return SchedulerHealth(SchedulerState.HALTED, readiness_reference)
        if not self.leases.acquire(self.config.lease_owner):
            return SchedulerHealth(SchedulerState.FAILED, readiness_reference, failed_cycles=1)

        records: list[SchedulerCycleRecord] = []
        quarantined: list[int] = []
        failed_cycles = 0
        last_successful: int | None = None
        state = SchedulerState.RUNNING

        try:
            for cycle_number in range(1, self.config.max_cycles_per_run + 1):
                self.leases.heartbeat(self.config.lease_owner)
                if self.emergency_stop.active():
                    state = SchedulerState.HALTED
                    break
                if self.control.shutdown_requested:
                    state = SchedulerState.IDLE
                    break
                if self.control.paused:
                    state = SchedulerState.PAUSED
                    break
                if self.control.draining and records:
                    state = SchedulerState.DRAINING
                    break

                if self.config.mode == DeploymentMode.OBSERVE_ONLY:
                    records.append(SchedulerCycleRecord(cycle_number, "observed"))
                    last_successful = cycle_number
                    if self.config.mode != DeploymentMode.ALWAYS_ON:
                        break
                    continue

                try:
                    result = self.runtime.run_cycle()
                except Exception as exc:
                    failed_cycles += 1
                    records.append(SchedulerCycleRecord(cycle_number, "failed", detail=str(exc)))
                    if self.config.mode != DeploymentMode.ALWAYS_ON:
                        state = SchedulerState.FAILED
                        break
                    continue

                status = str(result.get("status", "completed"))
                issue_number = result.get("issue_number")
                operation_ids = tuple(result.get("operation_ids", ()))
                detail = str(result.get("detail", ""))
                records.append(
                    SchedulerCycleRecord(
                        cycle_number,
                        status,
                        issue_number=issue_number,
                        detail=detail,
                        operation_ids=operation_ids,
                    )
                )
                if status == "quarantined" and issue_number is not None:
                    quarantined.append(int(issue_number))
                elif status == "completed":
                    last_successful = cycle_number
                elif status == "halted":
                    state = SchedulerState.HALTED
                    break
                else:
                    failed_cycles += 1

                if self.config.mode == DeploymentMode.SINGLE_CYCLE:
                    break

            if state == SchedulerState.RUNNING:
                state = SchedulerState.IDLE
        finally:
            self.leases.release(self.config.lease_owner)

        return SchedulerHealth(
            state=state,
            readiness_reference=readiness_reference,
            last_successful_cycle=last_successful,
            failed_cycles=failed_cycles,
            quarantined_issues=tuple(quarantined),
            cycles=tuple(records),
        )
