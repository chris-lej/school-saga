from __future__ import annotations

import unittest
from dataclasses import dataclass, field

from autonomy.production_loop import (
    GuardedProductionLoop,
    ProductionLoopConfig,
    ProductionLoopStatus,
    ReviewDecision,
)


@dataclass
class QueueFixture:
    issues: list[int]
    quarantined: list[tuple[int, str]] = field(default_factory=list)

    def next_ready_issue(self) -> int | None:
        return self.issues.pop(0) if self.issues else None

    def quarantine(self, issue_number: int, reason: str) -> None:
        self.quarantined.append((issue_number, reason))


@dataclass
class WorkerFixture:
    starts: int = 0
    fixes: int = 0

    def start(self, issue_number: int) -> tuple[int, str]:
        self.starts += 1
        return issue_number + 100, f"head-{issue_number}-0"

    def apply_fixes(self, issue_number: int, findings: tuple[str, ...]) -> str:
        self.fixes += 1
        return f"head-{issue_number}-{self.fixes}"


@dataclass
class ReviewerFixture:
    decisions: list[ReviewDecision]

    def review(self, pull_request_number: int, expected_head_sha: str) -> ReviewDecision:
        decision = self.decisions.pop(0)
        if decision.reviewed_head_sha == "EXPECTED":
            return ReviewDecision(decision.approved, decision.findings, expected_head_sha)
        return decision


@dataclass
class MergerFixture:
    merges: list[tuple[int, str]] = field(default_factory=list)

    def merge(self, pull_request_number: int, expected_head_sha: str) -> None:
        self.merges.append((pull_request_number, expected_head_sha))


@dataclass
class StopFixture:
    active_value: bool = False

    def active(self) -> bool:
        return self.active_value


class ProductionLoopTests(unittest.TestCase):
    def config(self, **changes) -> ProductionLoopConfig:
        values = {
            "enabled": True,
            "max_fix_iterations": 2,
            "max_issues_per_run": 1,
        }
        values.update(changes)
        return ProductionLoopConfig(**values)

    def test_approval_merges_expected_head(self):
        queue = QueueFixture([72])
        worker = WorkerFixture()
        reviewer = ReviewerFixture([ReviewDecision(True, reviewed_head_sha="EXPECTED")])
        merger = MergerFixture()
        result = GuardedProductionLoop(queue, worker, reviewer, merger, StopFixture(), self.config()).run()
        self.assertEqual(result.cycles[0].status, ProductionLoopStatus.COMPLETED)
        self.assertEqual(merger.merges, [(172, "head-72-0")])

    def test_requested_changes_return_to_worker_then_merge(self):
        queue = QueueFixture([72])
        worker = WorkerFixture()
        reviewer = ReviewerFixture(
            [
                ReviewDecision(False, ("Fix validation",), "EXPECTED"),
                ReviewDecision(True, reviewed_head_sha="EXPECTED"),
            ]
        )
        merger = MergerFixture()
        result = GuardedProductionLoop(queue, worker, reviewer, merger, StopFixture(), self.config()).run()
        self.assertEqual(result.cycles[0].fix_iterations, 1)
        self.assertEqual(worker.fixes, 1)
        self.assertEqual(merger.merges, [(172, "head-72-1")])

    def test_stale_review_head_quarantines_issue(self):
        queue = QueueFixture([72])
        result = GuardedProductionLoop(
            queue,
            WorkerFixture(),
            ReviewerFixture([ReviewDecision(True, reviewed_head_sha="stale")]),
            MergerFixture(),
            StopFixture(),
            self.config(),
        ).run()
        self.assertEqual(result.cycles[0].status, ProductionLoopStatus.QUARANTINED)
        self.assertEqual(queue.quarantined[0][0], 72)

    def test_iteration_limit_quarantines_without_merging(self):
        queue = QueueFixture([72])
        worker = WorkerFixture()
        reviewer = ReviewerFixture(
            [
                ReviewDecision(False, ("fix one",), "EXPECTED"),
                ReviewDecision(False, ("fix two",), "EXPECTED"),
            ]
        )
        merger = MergerFixture()
        result = GuardedProductionLoop(
            queue, worker, reviewer, merger, StopFixture(), self.config(max_fix_iterations=1)
        ).run()
        self.assertEqual(result.cycles[0].status, ProductionLoopStatus.QUARANTINED)
        self.assertEqual(merger.merges, [])

    def test_bounded_multi_cycle_selects_next_issue(self):
        queue = QueueFixture([72, 73])
        reviewer = ReviewerFixture(
            [
                ReviewDecision(True, reviewed_head_sha="EXPECTED"),
                ReviewDecision(True, reviewed_head_sha="EXPECTED"),
            ]
        )
        result = GuardedProductionLoop(
            queue,
            WorkerFixture(),
            reviewer,
            MergerFixture(),
            StopFixture(),
            self.config(max_issues_per_run=2),
        ).run()
        self.assertEqual([cycle.issue_number for cycle in result.cycles], [72, 73])

    def test_emergency_stop_prevents_selection(self):
        result = GuardedProductionLoop(
            QueueFixture([72]),
            WorkerFixture(),
            ReviewerFixture([]),
            MergerFixture(),
            StopFixture(True),
            self.config(),
        ).run()
        self.assertEqual(result.cycles, ())

    def test_disabled_configuration_fails_closed(self):
        with self.assertRaises(ValueError):
            GuardedProductionLoop(
                QueueFixture([72]),
                WorkerFixture(),
                ReviewerFixture([]),
                MergerFixture(),
                StopFixture(),
                ProductionLoopConfig(),
            ).run()


if __name__ == "__main__":
    unittest.main()
