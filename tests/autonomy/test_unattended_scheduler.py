from __future__ import annotations

from dataclasses import dataclass, field
import unittest

from autonomy.unattended_scheduler import (
    BoundedUnattendedScheduler,
    DeploymentMode,
    SchedulerControl,
    SchedulerState,
    UnattendedSchedulerConfig,
)


@dataclass
class ReadinessFixture:
    reference: str = "ready-report"
    calls: int = 0

    def verify(self) -> str:
        self.calls += 1
        return self.reference


@dataclass
class StopFixture:
    value: bool = False

    def active(self) -> bool:
        return self.value


@dataclass
class LeaseFixture:
    available: bool = True
    acquired: list[str] = field(default_factory=list)
    released: list[str] = field(default_factory=list)
    heartbeats: list[str] = field(default_factory=list)

    def acquire(self, owner: str) -> bool:
        if not self.available:
            return False
        self.acquired.append(owner)
        return True

    def release(self, owner: str) -> None:
        self.released.append(owner)

    def heartbeat(self, owner: str) -> None:
        self.heartbeats.append(owner)


@dataclass
class RuntimeFixture:
    results: list[dict]
    calls: int = 0

    def run_cycle(self) -> dict:
        self.calls += 1
        result = self.results.pop(0)
        error = result.get("raise")
        if error:
            raise RuntimeError(str(error))
        return result


class UnattendedSchedulerTests(unittest.TestCase):
    def config(self, **changes) -> UnattendedSchedulerConfig:
        values = {
            "mode": DeploymentMode.SINGLE_CYCLE,
            "max_cycles_per_run": 1,
            "lease_owner": "scheduler-1",
        }
        values.update(changes)
        return UnattendedSchedulerConfig(**values)

    def scheduler(self, runtime, *, stop=False, lease=True, control=None, config=None):
        return BoundedUnattendedScheduler(
            ReadinessFixture(),
            StopFixture(stop),
            LeaseFixture(lease),
            runtime,
            control or SchedulerControl(),
            config or self.config(),
        )

    def test_single_cycle_completes_and_releases_lease(self):
        runtime = RuntimeFixture([{"status": "completed", "issue_number": 80, "operation_ids": ("merge",)}])
        scheduler = self.scheduler(runtime)
        result = scheduler.run()
        self.assertEqual(result.state, SchedulerState.IDLE)
        self.assertEqual(result.last_successful_cycle, 1)
        self.assertEqual(result.cycles[0].issue_number, 80)
        self.assertEqual(runtime.calls, 1)

    def test_always_on_processes_multiple_issues(self):
        runtime = RuntimeFixture([
            {"status": "completed", "issue_number": 80},
            {"status": "quarantined", "issue_number": 81, "detail": "review limit"},
            {"status": "completed", "issue_number": 82},
        ])
        result = self.scheduler(
            runtime,
            config=self.config(mode=DeploymentMode.ALWAYS_ON, max_cycles_per_run=3),
        ).run()
        self.assertEqual(len(result.cycles), 3)
        self.assertEqual(result.quarantined_issues, (81,))
        self.assertEqual(result.last_successful_cycle, 3)

    def test_emergency_stop_blocks_before_lease(self):
        result = self.scheduler(RuntimeFixture([]), stop=True).run()
        self.assertEqual(result.state, SchedulerState.HALTED)
        self.assertEqual(result.cycles, ())

    def test_duplicate_lease_fails_closed(self):
        result = self.scheduler(RuntimeFixture([]), lease=False).run()
        self.assertEqual(result.state, SchedulerState.FAILED)
        self.assertEqual(result.failed_cycles, 1)

    def test_pause_prevents_cycle(self):
        control = SchedulerControl(paused=True)
        result = self.scheduler(RuntimeFixture([]), control=control).run()
        self.assertEqual(result.state, SchedulerState.PAUSED)
        self.assertEqual(result.cycles, ())

    def test_observe_only_performs_no_runtime_work(self):
        runtime = RuntimeFixture([])
        result = self.scheduler(
            runtime,
            config=self.config(mode=DeploymentMode.OBSERVE_ONLY),
        ).run()
        self.assertEqual(result.cycles[0].status, "observed")
        self.assertEqual(runtime.calls, 0)

    def test_runtime_failure_is_recorded(self):
        runtime = RuntimeFixture([{"raise": "temporary GitHub failure"}])
        result = self.scheduler(runtime).run()
        self.assertEqual(result.state, SchedulerState.FAILED)
        self.assertEqual(result.failed_cycles, 1)
        self.assertIn("temporary GitHub failure", result.cycles[0].detail)


if __name__ == "__main__":
    unittest.main()
