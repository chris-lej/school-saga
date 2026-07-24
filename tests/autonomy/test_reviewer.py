from __future__ import annotations

import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from autonomy.contracts import AuditEvent, IssueWorkRequest, Job, JobState, RepositoryTarget, WorkerResult, utc_now
from autonomy.github_adapter import DryRunMutationExecutor, GitHubAdapter
from autonomy.reviewer import DryRunReviewerAgent, ReviewerError
from autonomy.store import JsonJobStore


class FixtureTransport:
    def __init__(self, *, pr_state="open", draft=False, checks_state="success", head_sha="abc123"):
        self.pr_state = pr_state
        self.draft = draft
        self.checks_state = checks_state
        self.head_sha = head_sha

    def get_repository(self, repository):
        return {"owner": {"login": repository.owner}, "name": repository.name, "default_branch": "main"}

    def get_issue(self, repository, issue_number):
        raise AssertionError("not used")

    def get_pull_request(self, repository, pr_number):
        return {
            "number": pr_number,
            "state": self.pr_state,
            "draft": self.draft,
            "head": {"ref": "feature", "sha": self.head_sha},
            "base": {"ref": "main"},
        }

    def get_checks(self, repository, sha):
        return {"state": self.checks_state}


class ReviewerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = JsonJobStore(self.root / "jobs.json")
        self.job = Job(
            repository=RepositoryTarget(owner="chris-lej", name="school-saga"),
            request=IssueWorkRequest(issue_number=47, title="Reviewer fixture"),
        )
        self.store.create(self.job, "create-job")
        self.store.transition(self.job.job_id, JobState.CLAIMED, "claim")
        self.store.transition(self.job.job_id, JobState.EXECUTING, "execute")
        self.store.transition(self.job.job_id, JobState.VALIDATING, "validate")

    def tearDown(self):
        self.temp.cleanup()

    def persist_artifact(self, operation_id: str, payload: dict, event_type: str) -> None:
        event = AuditEvent(
            event_id=f"{self.job.job_id}:{event_type}:{operation_id}",
            job_id=self.job.job_id,
            operation_id=operation_id,
            event_type=event_type,
            timestamp=utc_now(),
            details=payload,
        )
        self.store.record_operation_result(self.job.job_id, operation_id, payload, event)

    def seed_worker_artifacts(self, *, validation_status="passed", commit_sha="abc123"):
        worker = WorkerResult(branch="feature", commit_sha=commit_sha, summary="fixture")
        self.persist_artifact(
            f"{self.job.job_id}:worker:result",
            {"worker_result": asdict(worker)},
            "worker.completed",
        )
        self.persist_artifact(
            f"{self.job.job_id}:worker:validation",
            {
                "operation_id": f"{self.job.job_id}:worker:validation",
                "attempt": 1,
                "status": validation_status,
                "steps": [],
                "started_at": utc_now(),
                "completed_at": utc_now(),
            },
            "validation.completed",
        )

    def agent(self, transport=None):
        mutations = DryRunMutationExecutor()
        agent = DryRunReviewerAgent(
            self.store,
            GitHubAdapter(transport or FixtureTransport()),
            mutations,
        )
        return agent, mutations

    def test_passing_inputs_reach_approved(self):
        self.seed_worker_artifacts()
        agent, mutations = self.agent()
        result = agent.run(self.job.job_id, 48)
        self.assertEqual(result.state, JobState.APPROVED)
        self.assertTrue(result.review_result.approved)
        self.assertEqual(result.report.reviewed_head_sha, "abc123")
        self.assertEqual(len(mutations.events()), 1)
        self.assertEqual(self.store.count_events(self.job.job_id, "reviewer.completed"), 1)

    def test_repeated_run_is_idempotent(self):
        self.seed_worker_artifacts()
        agent, mutations = self.agent()
        first = agent.run(self.job.job_id, 48)
        second = agent.run(self.job.job_id, 48)
        self.assertEqual(first.report, second.report)
        self.assertEqual(len(mutations.events()), 1)
        self.assertEqual(self.store.count_events(self.job.job_id, "reviewer.report.created"), 1)
        self.assertEqual(self.store.count_events(self.job.job_id, "reviewer.completed"), 1)

    def test_failing_validation_remains_reviewing(self):
        self.seed_worker_artifacts(validation_status="failed")
        result = self.agent()[0].run(self.job.job_id, 48)
        self.assertEqual(result.state, JobState.REVIEWING)
        self.assertFalse(result.review_result.approved)
        self.assertEqual(result.report.findings[0].code, "validation_failed")

    def test_draft_and_failed_checks_are_blocking(self):
        self.seed_worker_artifacts()
        transport = FixtureTransport(draft=True, checks_state="failure")
        result = self.agent(transport)[0].run(self.job.job_id, 48)
        self.assertFalse(result.review_result.approved)
        self.assertEqual({item.code for item in result.report.findings}, {"pr_is_draft", "checks_unsuccessful"})

    def test_stale_head_is_rejected(self):
        self.seed_worker_artifacts(commit_sha="oldsha")
        result = self.agent(FixtureTransport(head_sha="newsha"))[0].run(self.job.job_id, 48)
        self.assertFalse(result.review_result.approved)
        self.assertEqual(result.report.findings[0].code, "stale_head")

    def test_missing_worker_artifact_fails_actionably(self):
        with self.assertRaises(ReviewerError) as context:
            self.agent()[0].run(self.job.job_id, 48)
        self.assertIn("Missing required persisted artifact", str(context.exception))

    def test_rejects_worker_owned_state(self):
        other = Job(
            repository=RepositoryTarget(owner="chris-lej", name="school-saga"),
            request=IssueWorkRequest(issue_number=99, title="Other"),
        )
        self.store.create(other, "create-other")
        with self.assertRaises(ReviewerError):
            self.agent()[0].run(other.job_id, 48)


if __name__ == "__main__":
    unittest.main()
