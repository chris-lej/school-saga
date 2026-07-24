from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Protocol
from uuid import uuid4

from .contracts import AuditEvent, JobState, utc_now
from .orchestrator import DispatchResult, Orchestrator
from .store import JsonJobStore


class SchedulerMode(str, Enum):
    DISABLED = "disabled"
    DRY_RUN = "dry_run"
    PRODUCTION_GUARDED = "production_guarded"


@dataclass(frozen=True)
class ProductionReadinessManifest:
    repository_allowlist: tuple[str, ...]
    permitted_mutation_kinds: tuple[str, ...]
    required_checks: tuple[str, ...]
    merge_policy: str
    token_source: str
    rollback_procedure: str
    emergency_stop_source: str

    def validate(self) -> None:
        missing = []
        for name, value in asdict(self).items():
            if not value:
                missing.append(name)
        if missing:
            raise ValueError(f"Incomplete production-readiness manifest: {', '.join(missing)}")


@dataclass(frozen=True)
class SchedulerConfig:
    mode: SchedulerMode = SchedulerMode.DISABLED
    max_dispatches_per_cycle: int = 10
    max_concurrent_jobs: int = 1
    lease_seconds: int = 300
    retry_backoff_seconds: int = 60
    emergency_stop: bool = False
    readiness_manifest: ProductionReadinessManifest | None = None

    def validate(self) -> None:
        if self.max_dispatches_per_cycle < 1:
            raise ValueError("max_dispatches_per_cycle must be positive")
        if self.max_concurrent_jobs < 1:
            raise ValueError("max_concurrent_jobs must be positive")
        if self.lease_seconds < 1:
            raise ValueError("lease_seconds must be positive")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds cannot be negative")
        if self.mode == SchedulerMode.PRODUCTION_GUARDED:
            if self.readiness_manifest is None:
                raise ValueError("production_guarded mode requires a readiness manifest")
            self.readiness_manifest.validate()


@dataclass(frozen=True)
class SchedulerLease:
    job_id: str
    lease_id: str
    cycle_id: str
    acquired_at: str
    expires_at: str


@dataclass(frozen=True)
class ScheduledDispatch:
    job_id: str
    outcome: str
    dispatch: DispatchResult | None = None
    error: str = ""
    retryable: bool = False


@dataclass(frozen=True)
class SchedulerCycleResult:
    cycle_id: str
    mode: SchedulerMode
    halted: bool
    dispatches: tuple[ScheduledDispatch, ...] = field(default_factory=tuple)


class Scheduler(Protocol):
    def run_cycle(self, pull_request_lookup: Callable[[str], int | None]) -> SchedulerCycleResult: ...


class BoundedScheduler:
    """Runs one bounded scheduling cycle over persisted jobs."""

    def __init__(self, store: JsonJobStore, orchestrator: Orchestrator, config: SchedulerConfig):
        config.validate()
        self.store = store
        self.orchestrator = orchestrator
        self.config = config

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        return datetime.fromisoformat(value)

    def _lease_operation(self, job_id: str) -> str:
        return f"{job_id}:scheduler:lease"

    def _backoff_operation(self, job_id: str) -> str:
        return f"{job_id}:scheduler:backoff"

    def _active_lease(self, job_id: str, now: datetime) -> dict | None:
        lease = self.store.get_operation_result(self._lease_operation(job_id))
        if lease is None:
            return None
        if self._parse_timestamp(lease["expires_at"]) <= now:
            return None
        return lease

    def _in_backoff(self, job_id: str, now: datetime) -> bool:
        backoff = self.store.get_operation_result(self._backoff_operation(job_id))
        if backoff is None:
            return False
        return self._parse_timestamp(backoff["until"]) > now

    def _record(self, job_id: str, operation_id: str, event_type: str, payload: dict) -> dict:
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

    def _acquire_lease(self, job_id: str, cycle_id: str, now: datetime) -> SchedulerLease | None:
        if self._active_lease(job_id, now) is not None:
            return None
        lease = SchedulerLease(
            job_id=job_id,
            lease_id=str(uuid4()),
            cycle_id=cycle_id,
            acquired_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=self.config.lease_seconds)).isoformat(),
        )
        payload = asdict(lease)
        self._record(job_id, self._lease_operation(job_id), "scheduler.lease.acquired", payload)
        stored = self.store.get_operation_result(self._lease_operation(job_id))
        if stored is None or stored["lease_id"] != lease.lease_id:
            return None
        return lease

    def _record_backoff(self, job_id: str, now: datetime, reason: str) -> None:
        operation_id = self._backoff_operation(job_id)
        payload = {
            "until": (now + timedelta(seconds=self.config.retry_backoff_seconds)).isoformat(),
            "reason": reason,
        }
        self._record(job_id, operation_id, "scheduler.backoff.started", payload)

    def run_cycle(self, pull_request_lookup: Callable[[str], int | None]) -> SchedulerCycleResult:
        cycle_id = str(uuid4())
        if self.config.mode == SchedulerMode.DISABLED:
            return SchedulerCycleResult(cycle_id, self.config.mode, True)
        if self.config.emergency_stop:
            return SchedulerCycleResult(cycle_id, self.config.mode, True)

        now = datetime.now(timezone.utc)
        eligible = [
            job
            for job in self.store.list_jobs()
            if job.state not in {JobState.BLOCKED, JobState.FAILED, JobState.CANCELLED, JobState.COMPLETED}
            and not self._in_backoff(job.job_id, now)
        ]
        limit = min(self.config.max_concurrent_jobs, self.config.max_dispatches_per_cycle)
        results: list[ScheduledDispatch] = []

        for job in eligible[:limit]:
            lease = self._acquire_lease(job.job_id, cycle_id, now)
            if lease is None:
                continue
            try:
                pr_number = pull_request_lookup(job.job_id)
                dispatch = self.orchestrator.dispatch_once(job.job_id, pr_number)
                outcome = ScheduledDispatch(job_id=job.job_id, outcome="dispatched", dispatch=dispatch)
                self._record(
                    job.job_id,
                    f"{job.job_id}:scheduler:cycle:{cycle_id}",
                    "scheduler.dispatched",
                    {
                        "cycle_id": cycle_id,
                        "lease_id": lease.lease_id,
                        "from_state": dispatch.from_state.value,
                        "to_state": dispatch.to_state.value,
                        "agent": dispatch.agent,
                        "terminal": dispatch.terminal,
                    },
                )
            except Exception as exc:  # policy boundary: preserve failure instead of looping
                retryable = not isinstance(exc, (KeyError, ValueError))
                outcome = ScheduledDispatch(
                    job_id=job.job_id,
                    outcome="failed",
                    error=str(exc),
                    retryable=retryable,
                )
                if retryable and self.config.retry_backoff_seconds:
                    self._record_backoff(job.job_id, now, str(exc))
                self._record(
                    job.job_id,
                    f"{job.job_id}:scheduler:cycle:{cycle_id}",
                    "scheduler.dispatch.failed",
                    {
                        "cycle_id": cycle_id,
                        "lease_id": lease.lease_id,
                        "error": str(exc),
                        "retryable": retryable,
                    },
                )
            results.append(outcome)

        return SchedulerCycleResult(cycle_id, self.config.mode, False, tuple(results))
