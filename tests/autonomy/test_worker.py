from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autonomy.contracts import IssueWorkRequest, Job, JobState, RepositoryTarget
from autonomy.github_adapter import DryRunMutationExecutor, GitHubAdapter
from autonomy.store import JsonJobStore
from autonomy.validation import ValidationCommand, ValidationService, ValidationStatus, ValidationStepResult
from autonomy.worker import DryRunWorkerAgent, WorkerError


class FixtureTransport:
    def __init__(self, *, state="open", labels=("state:ready",)):
        self.state = state
        self.labels = labels

    def get_repository(self, repository):
        return {"owner": {"login": repository.owner}, "name": repository.name, "default_branch": "main"}

    def get_issue(self, repository, issue_number):
        return {
            "number": issue_number,
            "title": "Worker fixture",
            "body": "## Acceptance criteria\n- [ ] first criterion\n- [ ] second criterion",
            "state": self.state,
            "labels": [{"name": label} for label in self.labels],
        }

    def get_pull_request(self, repository, pr_number):
        raise AssertionError("not used")

    def get_checks(self, repository, sha):
        raise AssertionError("not used")


class PassingRunner:
    def __init__(self):
        self.calls = 0

    def run(self, command, *, cwd, environment, max_output_chars):
        self.calls += 1
        return ValidationStepResult(command.name, ValidationStatus.PASSED, 0, stdout="ok")


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = JsonJobStore(self.root / "jobs.json")
        self.job = Job(
            repository=RepositoryTarget(owner="chris-lej", name="school-saga"),
            request=IssueWorkRequest(issue_number=45, title="Worker fixture"),
        )
        self.store.create(self.job, "create-job")

    def tearDown(self):
        self.temp.cleanup()

    def agent(self, transport=None, runner=None):
        runner = runner or PassingRunner()
        validation = ValidationService(
            self.store,
            runner,
            commands=(ValidationCommand("fixture", ("fixture",)),),
            cwd=self.root,
        )
        return DryRunWorkerAgent(
            self.store,
            GitHubAdapter(transport or FixtureTransport()),
            DryRunMutationExecutor(),
            validation,
        ), runner

    def test_ready_issue_reaches_validating_with_plan_and_result(self):
        agent, runner = self.agent()
        result = agent.run(self.job.job_id)
        self.assertEqual(result.state, JobState.VALIDATING)
        self.assertEqual(result.plan.acceptance_items, ("first criterion", "second criterion"))
        self.assertEqual(result.validation.status, ValidationStatus.PASSED)
        self.assertEqual(runner.calls, 1)
        self.assertEqual(self.store.count_events(self.job.job_id, "worker.plan.created"), 1)
        self.assertEqual(self.store.count_events(self.job.job_id, "worker.completed"), 1)

    def test_repeated_run_is_idempotent(self):
        agent, runner = self.agent()
        first = agent.run(self.job.job_id)
        second = agent.run(self.job.job_id)
        self.assertEqual(first.plan, second.plan)
        self.assertEqual(runner.calls, 1)
        self.assertEqual(self.store.count_events(self.job.job_id, "worker.plan.created"), 1)
        self.assertEqual(self.store.count_events(self.job.job_id, "validation.completed"), 1)
        self.assertEqual(self.store.count_events(self.job.job_id, "worker.completed"), 1)

    def test_resume_from_claimed(self):
        self.store.transition(self.job.job_id, JobState.CLAIMED, "manual-claim")
        agent, _ = self.agent()
        result = agent.run(self.job.job_id)
        self.assertEqual(result.state, JobState.VALIDATING)
        self.assertEqual(self.store.get(self.job.job_id).attempts, 1)

    def test_ineligible_issue_is_blocked(self):
        agent, _ = self.agent(FixtureTransport(labels=()))
        with self.assertRaises(WorkerError):
            agent.run(self.job.job_id)
        self.assertEqual(self.store.get(self.job.job_id).state, JobState.BLOCKED)
        self.assertEqual(self.store.count_events(self.job.job_id, "worker.blocked"), 1)

    def test_worker_rejects_reviewer_owned_state(self):
        self.store.transition(self.job.job_id, JobState.CLAIMED, "claim")
        self.store.transition(self.job.job_id, JobState.EXECUTING, "execute")
        self.store.transition(self.job.job_id, JobState.VALIDATING, "validate")
        self.store.transition(self.job.job_id, JobState.REVIEWING, "review")
        agent, _ = self.agent()
        with self.assertRaises(WorkerError):
            agent.run(self.job.job_id)


if __name__ == "__main__":
    unittest.main()
