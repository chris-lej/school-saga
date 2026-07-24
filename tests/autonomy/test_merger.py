from __future__ import annotations

import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from autonomy.contracts import AuditEvent, IssueWorkRequest, Job, JobState, RepositoryTarget, ReviewResult, utc_now
from autonomy.github_adapter import DryRunMutationExecutor, GitHubAdapter
from autonomy.merger import DryRunMergerAgent, MergerError
from autonomy.store import JsonJobStore


class FixtureTransport:
    def __init__(self, *, pr_state="open", draft=False, checks_state="success", head_sha="abc123", base_branch="main"):
        self.pr_state = pr_state
        self.draft = draft
        self.checks_state = checks_state
        self.head_sha = head_sha
        self.base_branch = base_branch

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
            "base": {"ref": self.base_branch},
        }

    def get_checks(self, repository, sha):
        return {"state": self.checks_state}


class MergerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = JsonJobStore(self.root / "jobs.json")
        self.job = Job(
            repository=RepositoryTarget(owner="chris-lej", name="school-saga"),
            request=IssueWorkRequest(issue_number=49, title="Merger fixture"),
        )
        self.store.create(self.job, "create-job")
        self.store.transition(self.job.job_id, JobState.CLAIMED, "claim")
        self.store.transition(self.job.job_id, JobState.EXECUTING, "execute")
        self.store.transition(self.job.job_id, JobState.VALIDATING, "validate")
        self.store.transition(self.job.job_id, JobState.REVIEWING, "review")
        self.store.transition(self.job.job_id, JobState.APPROVED, "approve")

    def tearDown(self):
        self.temp.cleanup()

    def persist(self, operation_id: str, payload: dict, event_type: str) -> None:
        event = AuditEvent(
            event_id=f"{self.job.job_id}:{event_type}:{operation_id}",
            job_id=self.job.job_id,
            operation_id=operation_id,
            event_type=event_type,
            timestamp=utc_now(),
            details=payload,
        )
        self.store.record_operation_result(self.job.job_id, operation_id, payload, event)

    def seed_artifacts(self, *, approved=True, reviewed_head_sha="abc123", validation_status="passed"):
        self.persist(
            f"{self.job.job_id}:reviewer:result",
            {
                "review_result": asdict(ReviewResult(approved=approved, summary="fixture")),
                "reviewed_head_sha": reviewed_head_sha,
                "findings": [],
            },
            "reviewer.completed",
        )
        self.persist(
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
        return DryRunMergerAgent(
            self.store,
            GitHubAdapter(transport or FixtureTransport()),
            DryRunMutationExecutor(),
        )

    def test_approved_job_reaches_completed(self):
        self.seed_artifacts()
        result = self.agent().run(self.job.job_id, 50)
        self.assertTrue(result.decision.allowed)
        self.assertEqual(result.state, JobState.COMPLETED)
        self.assertEqual(result.report.expected_head_sha, "abc123")
        self.assertEqual(self.store.count_events(self.job.job_id, "merger.completed"), 1)

    def test_stale_approval_is_blocked_without_transition(self):
        self.seed_artifacts(reviewed_head_sha="oldsha")
        result = self.agent().run(self.job.job_id, 50)
        self.assertFalse(result.decision.allowed)
        self.assertEqual(result.state, JobState.APPROVED)
        self.assertIn("stale_approval", {finding.code for finding in result.report.findings})

    def test_failing_checks_are_blocked(self):
        self.seed_artifacts()
        result = self.agent(FixtureTransport(checks_state="failure")).run(self.job.job_id, 50)
        self.assertFalse(result.decision.allowed)
        self.assertIn("checks_unsuccessful", {finding.code for finding in result.report.findings})

    def test_base_branch_mismatch_is_blocked(self):
        self.seed_artifacts()
        result = self.agent(FixtureTransport(base_branch="release")).run(self.job.job_id, 50)
        self.assertFalse(result.decision.allowed)
        self.assertIn("base_branch_mismatch", {finding.code for finding in result.report.findings})

    def test_restart_at_merging_is_idempotent(self):
        self.seed_artifacts()
        self.store.transition(self.job.job_id, JobState.MERGING, "seed-merging")
        agent = self.agent()
        first = agent.run(self.job.job_id, 50)
        self.assertEqual(first.state, JobState.COMPLETED)
        with self.assertRaises(MergerError):
            agent.run(self.job.job_id, 50)
        self.assertEqual(self.store.count_events(self.job.job_id, "merger.completed"), 1)

    def test_missing_review_artifact_fails_safely(self):
        with self.assertRaises(MergerError):
            self.agent().run(self.job.job_id, 50)


if __name__ == "__main__":
    unittest.main()
