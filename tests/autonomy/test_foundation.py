from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autonomy.contracts import IssueWorkRequest, Job, JobState, RepositoryTarget
from autonomy.store import JsonJobStore


class FoundationTests(unittest.TestCase):
    def make_job(self) -> Job:
        return Job(
            repository=RepositoryTarget(owner="chris-lej", name="school-saga"),
            request=IssueWorkRequest(issue_number=39, title="Foundation"),
        )

    def test_serialization_round_trip(self) -> None:
        job = self.make_job()
        self.assertEqual(Job.from_dict(job.to_dict()).to_dict(), job.to_dict())

    def test_invalid_transition_is_actionable(self) -> None:
        job = self.make_job()
        with self.assertRaisesRegex(ValueError, "allowed targets"):
            job.transition(JobState.COMPLETED)

    def test_transition_is_idempotent_by_operation_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = JsonJobStore(Path(directory) / "jobs.json")
            job = store.create(self.make_job(), "create-39")
            first = store.transition(job.job_id, JobState.CLAIMED, "claim-39")
            second = store.transition(job.job_id, JobState.CLAIMED, "claim-39")
            self.assertEqual(first.to_dict(), second.to_dict())
            self.assertEqual(len(store.list_events(job.job_id)), 2)

    def test_restart_recovers_persisted_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.json"
            first_store = JsonJobStore(path)
            job = first_store.create(self.make_job(), "create-39")
            first_store.transition(job.job_id, JobState.CLAIMED, "claim-39")
            second_store = JsonJobStore(path)
            self.assertEqual(second_store.get(job.job_id).state, JobState.CLAIMED)

    def test_incompatible_store_fails_safely(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.json"
            path.write_text(json.dumps({"schema_version": 999}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Unsupported store schema version"):
                JsonJobStore(path).list_jobs()


if __name__ == "__main__":
    unittest.main()
