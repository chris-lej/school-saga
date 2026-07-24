from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol

from .contracts import AuditEvent, JobState, utc_now
from .merger import MergerAgent
from .reviewer import ReviewerAgent
from .store import JsonJobStore
from .worker import WorkerAgent


class OrchestratorError(RuntimeError):
    pass


@dataclass(frozen=True)
class DispatchResult:
    job_id: str
    from_state: JobState
    to_state: JobState
    agent: str
    operation_id: str
    terminal: bool


class Orchestrator(Protocol):
    def dispatch_once(self, job_id: str, pull_request_number: int | None = None) -> DispatchResult: ...


class DryRunOrchestrator:
    """Persisted single-step dispatcher for the dry-run agent lifecycle."""

    def __init__(
        self,
        store: JsonJobStore,
        worker: WorkerAgent,
        reviewer: ReviewerAgent,
        merger: MergerAgent,
    ):
        self.store = store
        self.worker = worker
        self.reviewer = reviewer
        self.merger = merger

    @staticmethod
    def _operation(job_id: str, state: JobState) -> str:
        return f"{job_id}:orchestrator:dispatch:{state.value}"

    def _persist(self, job_id: str, operation_id: str, payload: dict) -> dict:
        existing = self.store.get_operation_result(operation_id)
        if existing is not None:
            return existing
        event = AuditEvent(
            event_id=f"{job_id}:orchestrator:{operation_id}",
            job_id=job_id,
            operation_id=operation_id,
            event_type="orchestrator.dispatched",
            timestamp=utc_now(),
            details=payload,
        )
        return self.store.record_operation_result(job_id, operation_id, payload, event)

    def dispatch_once(self, job_id: str, pull_request_number: int | None = None) -> DispatchResult:
        job = self.store.get(job_id)
        initial = job.state
        operation_id = self._operation(job_id, initial)
        existing = self.store.get_operation_result(operation_id)
        if existing is not None:
            return DispatchResult(
                job_id=job_id,
                from_state=JobState(existing["from_state"]),
                to_state=JobState(existing["to_state"]),
                agent=existing["agent"],
                operation_id=operation_id,
                terminal=bool(existing["terminal"]),
            )

        if initial in {JobState.BLOCKED, JobState.FAILED, JobState.CANCELLED, JobState.COMPLETED}:
            result = DispatchResult(job_id, initial, initial, "none", operation_id, True)
        elif initial in {JobState.QUEUED, JobState.CLAIMED, JobState.EXECUTING}:
            self.worker.run(job_id)
            result = DispatchResult(job_id, initial, self.store.get(job_id).state, "worker", operation_id, False)
        elif initial == JobState.VALIDATING:
            if pull_request_number is None:
                raise OrchestratorError("Reviewer dispatch requires a pull-request number")
            self.reviewer.run(job_id, pull_request_number)
            result = DispatchResult(job_id, initial, self.store.get(job_id).state, "reviewer", operation_id, False)
        elif initial == JobState.REVIEWING:
            if pull_request_number is None:
                raise OrchestratorError("Reviewer resume requires a pull-request number")
            self.reviewer.run(job_id, pull_request_number)
            result = DispatchResult(job_id, initial, self.store.get(job_id).state, "reviewer", operation_id, False)
        elif initial in {JobState.APPROVED, JobState.MERGING}:
            if pull_request_number is None:
                raise OrchestratorError("Merger dispatch requires a pull-request number")
            self.merger.run(job_id, pull_request_number)
            final_state = self.store.get(job_id).state
            result = DispatchResult(job_id, initial, final_state, "merger", operation_id, final_state == JobState.COMPLETED)
        else:
            raise OrchestratorError(f"Unsupported job state: {initial.value}")

        self._persist(
            job_id,
            operation_id,
            {
                "from_state": result.from_state.value,
                "to_state": result.to_state.value,
                "agent": result.agent,
                "terminal": result.terminal,
            },
        )
        return result

    def run_to_terminal(
        self,
        job_id: str,
        pull_request_number: int,
        *,
        max_dispatches: int = 10,
    ) -> tuple[DispatchResult, ...]:
        results: list[DispatchResult] = []
        for _ in range(max_dispatches):
            current = self.store.get(job_id).state
            result = self.dispatch_once(job_id, pull_request_number)
            results.append(result)
            if result.terminal:
                return tuple(results)
            if self.store.get(job_id).state == current:
                raise OrchestratorError(f"Dispatch made no lifecycle progress from {current.value!r}")
        raise OrchestratorError(f"Job did not reach a terminal state within {max_dispatches} dispatches")
