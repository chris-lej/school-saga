from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from autonomy.contracts import IssueWorkRequest, Job, JobState, RepositoryTarget
from autonomy.orchestrator import DispatchResult
from autonomy.scheduler import (
    BoundedScheduler,
    ProductionReadinessManifest,
    SchedulerConfig,
    SchedulerMode,
)
from autonomy.store import JsonJobStore


@dataclass
class FixtureOrchestrator:
    store: JsonJobStore
    calls: int = 0
    fail: bool = False

    def dispatch_once(self, job_id: str, pull_request_number: int | None = None) -> DispatchResult:
        self.calls += 1
        if self.fail:
            raise RuntimeError("temporary fixture failure")
        job = self.store.get(job_id)
        initial = job.state
        if initial == JobState.QUEUED:
            self.store.transition(job_id, JobState.CLAIMED, f"{job_id}:fixture:claim")
        return DispatchResult(
            job_id=job_id,
            from_state=initial,
            to_state=self.store.get(job_id).state,
            agent="fixture",
            operation_id=f"{job_id}:fixture:dispatch",
            terminal=False,
        )


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = JsonJobStore(self.root / "jobs.json")

    def tearDown(self):
        self.temp.cleanup()

    def create_job(self, number: int) -> Job:
        job = Job(
            repository=RepositoryTarget(owner="chris-lej", name="school-saga"),
            request=IssueWorkRequest(issue_number=number, title=f"Fixture {number}"),
        )
        self.store.create(job, f"create-{number}")
        return job

    def test_disabled_mode_halts_without_dispatch(self):
        job = self.create_job(1)
        orchestrator = FixtureOrchestrator(self.store)
        scheduler = BoundedScheduler(
            self.store,
            orchestrator,
            SchedulerConfig(mode=SchedulerMode.DISABLED),
        )
        result = scheduler.run_cycle(lambda _: None)
        self.assertTrue(result.halted)
        self.assertEqual(orchestrator.calls, 0)
        self.assertEqual(self.store.get(job.job_id).state, JobState.QUEUED)

    def test_emergency_stop_halts_without_corrupting_jobs(self):
        job = self.create_job(2)
        orchestrator = FixtureOrchestrator(self.store)
        scheduler = BoundedScheduler(
            self.store,
            orchestrator,
            SchedulerConfig(mode=SchedulerMode.DRY_RUN, emergency_stop=True),
        )
        result = scheduler.run_cycle(lambda _: None)
        self.assertTrue(result.halted)
        self.assertEqual(self.store.get(job.job_id).state, JobState.QUEUED)

    def test_cycle_respects_dispatch_and_concurrency_bounds(self):
        jobs = [self.create_job(number) for number in (3, 4, 5)]
        orchestrator = FixtureOrchestrator(self.store)
        scheduler = BoundedScheduler(
            self.store,
            orchestrator,
            SchedulerConfig(
                mode=SchedulerMode.DRY_RUN,
                max_concurrent_jobs=2,
                max_dispatches_per_cycle=3,
            ),
        )
        result = scheduler.run_cycle(lambda _: None)
        self.assertEqual(len(result.dispatches), 2)
        self.assertEqual(orchestrator.calls, 2)
        transitioned = sum(self.store.get(job.job_id).state == JobState.CLAIMED for job in jobs)
        self.assertEqual(transitioned, 2)

    def test_active_lease_prevents_duplicate_dispatch(self):
        job = self.create_job(6)
        orchestrator = FixtureOrchestrator(self.store)
        config = SchedulerConfig(mode=SchedulerMode.DRY_RUN, lease_seconds=300)
        first = BoundedScheduler(self.store, orchestrator, config)
        second = BoundedScheduler(self.store, orchestrator, config)
        first.run_cycle(lambda _: None)
        second.run_cycle(lambda _: None)
        self.assertEqual(orchestrator.calls, 1)
        self.assertEqual(self.store.count_events(job.job_id, "scheduler.lease.acquired"), 1)

    def test_retryable_failure_records_backoff(self):
        job = self.create_job(7)
        orchestrator = FixtureOrchestrator(self.store, fail=True)
        scheduler = BoundedScheduler(
            self.store,
            orchestrator,
            SchedulerConfig(mode=SchedulerMode.DRY_RUN, retry_backoff_seconds=120),
        )
        first = scheduler.run_cycle(lambda _: None)
        second = scheduler.run_cycle(lambda _: None)
        self.assertEqual(first.dispatches[0].outcome, "failed")
        self.assertTrue(first.dispatches[0].retryable)
        self.assertEqual(len(second.dispatches), 0)
        self.assertIsNotNone(self.store.get_operation_result(f"{job.job_id}:scheduler:backoff"))

    def test_production_guarded_requires_complete_manifest(self):
        with self.assertRaises(ValueError):
            BoundedScheduler(
                self.store,
                FixtureOrchestrator(self.store),
                SchedulerConfig(mode=SchedulerMode.PRODUCTION_GUARDED),
            )

        manifest = ProductionReadinessManifest(
            repository_allowlist=("chris-lej/school-saga",),
            permitted_mutation_kinds=("claim_issue",),
            required_checks=("Godot Validation",),
            merge_policy="approval and expected-head required",
            token_source="runtime secret manager",
            rollback_procedure="disable scheduler and revoke token",
            emergency_stop_source="AUTONOMY_EMERGENCY_STOP",
        )
        scheduler = BoundedScheduler(
            self.store,
            FixtureOrchestrator(self.store),
            SchedulerConfig(
                mode=SchedulerMode.PRODUCTION_GUARDED,
                readiness_manifest=manifest,
            ),
        )
        self.assertEqual(scheduler.config.mode, SchedulerMode.PRODUCTION_GUARDED)


if __name__ == "__main__":
    unittest.main()
