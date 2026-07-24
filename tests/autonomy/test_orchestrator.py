from __future__ import annotations

import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from autonomy.contracts import AuditEvent, IssueWorkRequest, Job, JobState, RepositoryTarget, ReviewResult, WorkerResult, utc_now
from autonomy.github_adapter import DryRunMutationExecutor, GitHubAdapter
from autonomy.merger import DryRunMergerAgent
from autonomy.orchestrator import DryRunOrchestrator, OrchestratorError
from autonomy.reviewer import DryRunReviewerAgent
from autonomy.store import JsonJobStore
from autonomy.validation import ValidationCommand, ValidationService, ValidationStatus, ValidationStepResult
from autonomy.worker import DryRunWorkerAgent


class FixtureTransport:
    def get_repository(self, repository):
        return {"owner": {"login": repository.owner}, "name": repository.name, "default_branch": "main"}

    def get_issue(self, repository, issue_number):
        return {
            "number": issue_number,
            "title": "Orchestrator fixture",
            "body": "## Acceptance criteria\n- [ ] complete lifecycle",
            "state": "open",
            "labels": [{"name": "state:ready"}],
        }

    def get_pull_request(self, repository, pr_number):
        return {
            "number": pr_number,
            "state": "open",
            "draft": False,
            "head": {"ref": "autonomy/issue-51", "sha": "abc123"},
            "base": {"ref": "main"},
        }

    def get_checks(self, repository, sha):
        return {"state": "success"}


class PassingRunner:
    def run(self, command, *, cwd, environment, max_output_chars):
        return ValidationStepResult(command.name, ValidationStatus.PASSED, 0, stdout="ok")


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = JsonJobStore(self.root / "jobs.json")
        self.job = Job(
            repository=RepositoryTarget(owner="chris-lej", name="school-saga"),
            request=IssueWorkRequest(issue_number=51, title="Orchestrator fixture"),
        )
        self.store.create(self.job, "create-job")
        github = GitHubAdapter(FixtureTransport())
        mutations = DryRunMutationExecutor()
        validation = ValidationService(
            self.store,
            PassingRunner(),
            commands=(ValidationCommand("fixture", ("fixture",)),),
            cwd=self.root,
        )
        self.worker = DryRunWorkerAgent(self.store, github, mutations, validation)
        self.reviewer = DryRunReviewerAgent(self.store, github, mutations)
        self.merger = DryRunMergerAgent(self.store, github, mutations)
        self.orchestrator = DryRunOrchestrator(self.store, self.worker, self.reviewer, self.merger)

    def tearDown(self):
        self.temp.cleanup()

    def seed_worker_commit(self):
        operation_id = f"{self.job.job_id}:worker:result"
        payload = {
            "worker_result": asdict(WorkerResult(branch="autonomy/issue-51", commit_sha="abc123")),
            "validation_operation_id": f"{self.job.job_id}:worker:validation",
            "validation_status": "passed",
        }
        event = AuditEvent(
            event_id=f"{self.job.job_id}:worker.completed:{operation_id}",
            job_id=self.job.job_id,
            operation_id=operation_id,
            event_type="worker.completed",
            timestamp=utc_now(),
            details=payload,
        )
        existing = self.store.get_operation_result(operation_id)
        if existing is None:
            self.store.record_operation_result(self.job.job_id, operation_id, payload, event)

    def test_end_to_end_dry_run_reaches_completed(self):
        worker_dispatch = self.orchestrator.dispatch_once(self.job.job_id, 60)
        self.assertEqual(worker_dispatch.agent, "worker")
        self.assertEqual(self.store.get(self.job.job_id).state, JobState.VALIDATING)
        self.seed_worker_commit()

        reviewer_dispatch = self.orchestrator.dispatch_once(self.job.job_id, 60)
        self.assertEqual(reviewer_dispatch.agent, "reviewer")
        self.assertEqual(self.store.get(self.job.job_id).state, JobState.APPROVED)

        merger_dispatch = self.orchestrator.dispatch_once(self.job.job_id, 60)
        self.assertEqual(merger_dispatch.agent, "merger")
        self.assertTrue(merger_dispatch.terminal)
        self.assertEqual(self.store.get(self.job.job_id).state, JobState.COMPLETED)
        self.assertEqual(self.store.count_events(self.job.job_id, "orchestrator.dispatched"), 3)

    def test_repeating_dispatch_operation_is_idempotent(self):
        first = self.orchestrator.dispatch_once(self.job.job_id, 60)
        second = self.orchestrator.dispatch_once(self.job.job_id, 60)
        self.assertEqual(first, second)
        self.assertEqual(self.store.count_events(self.job.job_id, "orchestrator.dispatched"), 1)

    def test_reviewer_requires_pr_linkage(self):
        self.orchestrator.dispatch_once(self.job.job_id, 60)
        with self.assertRaises(OrchestratorError):
            self.orchestrator.dispatch_once(self.job.job_id)


if __name__ == "__main__":
    unittest.main()
