from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class ProductionLoopStatus(str, Enum):
    COMPLETED = "completed"
    QUARANTINED = "quarantined"
    HALTED = "halted"
    FAILED = "failed"


@dataclass(frozen=True)
class ReviewDecision:
    approved: bool
    findings: tuple[str, ...] = field(default_factory=tuple)
    reviewed_head_sha: str | None = None


@dataclass(frozen=True)
class ProductionLoopConfig:
    enabled: bool = False
    max_fix_iterations: int = 3
    max_issues_per_run: int = 1
    one_active_job: bool = True
    unattended_scheduler_enabled: bool = False

    def validate(self) -> None:
        if not self.enabled:
            raise ValueError("Production loop is disabled")
        if self.max_fix_iterations < 0:
            raise ValueError("max_fix_iterations must be non-negative")
        if self.max_issues_per_run < 1:
            raise ValueError("max_issues_per_run must be at least one")
        if not self.one_active_job:
            raise ValueError("Exactly one active job is required")
        if self.unattended_scheduler_enabled:
            raise ValueError("Unattended scheduling remains disabled")


class EmergencyStop(Protocol):
    def active(self) -> bool: ...


class QueueAdapter(Protocol):
    def next_ready_issue(self) -> int | None: ...
    def quarantine(self, issue_number: int, reason: str) -> None: ...


class WorkerAdapter(Protocol):
    def start(self, issue_number: int) -> tuple[int, str]: ...
    def apply_fixes(self, issue_number: int, findings: tuple[str, ...]) -> str: ...


class ReviewerAdapter(Protocol):
    def review(self, pull_request_number: int, expected_head_sha: str) -> ReviewDecision: ...


class MergerAdapter(Protocol):
    def merge(self, pull_request_number: int, expected_head_sha: str) -> None: ...


@dataclass(frozen=True)
class IssueCycleResult:
    issue_number: int
    status: ProductionLoopStatus
    pull_request_number: int | None = None
    head_sha: str | None = None
    fix_iterations: int = 0
    detail: str = ""


@dataclass(frozen=True)
class ProductionLoopRunResult:
    cycles: tuple[IssueCycleResult, ...]


class GuardedProductionLoop:
    """Bounded Worker -> Reviewer -> fixes -> Reviewer -> Merger controller."""

    def __init__(
        self,
        queue: QueueAdapter,
        worker: WorkerAdapter,
        reviewer: ReviewerAdapter,
        merger: MergerAdapter,
        emergency_stop: EmergencyStop,
        config: ProductionLoopConfig,
    ):
        self.queue = queue
        self.worker = worker
        self.reviewer = reviewer
        self.merger = merger
        self.emergency_stop = emergency_stop
        self.config = config

    def _stopped(self) -> bool:
        return self.emergency_stop.active()

    def run(self) -> ProductionLoopRunResult:
        self.config.validate()
        results: list[IssueCycleResult] = []

        for _ in range(self.config.max_issues_per_run):
            if self._stopped():
                break
            issue_number = self.queue.next_ready_issue()
            if issue_number is None:
                break
            results.append(self._run_issue(issue_number))

        return ProductionLoopRunResult(tuple(results))

    def _run_issue(self, issue_number: int) -> IssueCycleResult:
        if self._stopped():
            return IssueCycleResult(issue_number, ProductionLoopStatus.HALTED, detail="Emergency stop active")

        try:
            pull_request_number, head_sha = self.worker.start(issue_number)
        except Exception as exc:
            self.queue.quarantine(issue_number, str(exc))
            return IssueCycleResult(issue_number, ProductionLoopStatus.QUARANTINED, detail=str(exc))

        fix_iterations = 0
        while True:
            if self._stopped():
                return IssueCycleResult(
                    issue_number,
                    ProductionLoopStatus.HALTED,
                    pull_request_number,
                    head_sha,
                    fix_iterations,
                    "Emergency stop active",
                )

            decision = self.reviewer.review(pull_request_number, head_sha)
            if decision.reviewed_head_sha != head_sha:
                reason = "Reviewer head SHA did not match expected head"
                self.queue.quarantine(issue_number, reason)
                return IssueCycleResult(
                    issue_number,
                    ProductionLoopStatus.QUARANTINED,
                    pull_request_number,
                    head_sha,
                    fix_iterations,
                    reason,
                )

            if decision.approved:
                if self._stopped():
                    return IssueCycleResult(
                        issue_number,
                        ProductionLoopStatus.HALTED,
                        pull_request_number,
                        head_sha,
                        fix_iterations,
                        "Emergency stop active",
                    )
                self.merger.merge(pull_request_number, head_sha)
                return IssueCycleResult(
                    issue_number,
                    ProductionLoopStatus.COMPLETED,
                    pull_request_number,
                    head_sha,
                    fix_iterations,
                )

            if fix_iterations >= self.config.max_fix_iterations:
                reason = "Maximum fix iterations exceeded"
                self.queue.quarantine(issue_number, reason)
                return IssueCycleResult(
                    issue_number,
                    ProductionLoopStatus.QUARANTINED,
                    pull_request_number,
                    head_sha,
                    fix_iterations,
                    reason,
                )

            if not decision.findings:
                reason = "Reviewer requested changes without actionable findings"
                self.queue.quarantine(issue_number, reason)
                return IssueCycleResult(
                    issue_number,
                    ProductionLoopStatus.QUARANTINED,
                    pull_request_number,
                    head_sha,
                    fix_iterations,
                    reason,
                )

            head_sha = self.worker.apply_fixes(issue_number, decision.findings)
            fix_iterations += 1
