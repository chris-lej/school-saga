from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autonomy.contracts import IssueWorkRequest, Job, RepositoryTarget
from autonomy.github_adapter import AdapterErrorKind, GitHubAdapterError, MutationCommand, MutationKind
from autonomy.production_github import (
    GuardedGitHubMutationTransport,
    ProductionMutationConfig,
)
from autonomy.scheduler import ProductionReadinessManifest, SchedulerMode
from autonomy.store import JsonJobStore


class FakeClient:
    def __init__(self):
        self.calls = []

    def claim_issue(self, repository, issue_number):
        self.calls.append(("claim", repository, issue_number))
        return {"claimed": True}

    def create_branch(self, repository, branch, base):
        self.calls.append(("branch", repository, branch, base))
        return {"branch": branch}

    def open_pull_request(self, repository, *, title, body, head, base):
        self.calls.append(("pr", repository, head, base))
        return {"number": 101}

    def submit_review(self, repository, *, pull_request_number, event, reviewed_head_sha):
        self.calls.append(("review", repository, pull_request_number, event, reviewed_head_sha))
        return {"submitted": True}

    def merge_pull_request(self, repository, *, pull_request_number, merge_method, expected_head_sha):
        self.calls.append(("merge", repository, pull_request_number, merge_method, expected_head_sha))
        return {"merged": True}


class ProductionGitHubTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = JsonJobStore(Path(self.temp.name) / "jobs.json")
        self.job = Job(
            repository=RepositoryTarget(owner="chris-lej", name="school-saga"),
            request=IssueWorkRequest(issue_number=55, title="fixture"),
        )
        self.store.create(self.job, "create-job")
        self.manifest = ProductionReadinessManifest(
            repository_allowlist=("chris-lej/school-saga",),
            permitted_mutation_kinds=tuple(kind.value for kind in MutationKind),
            required_checks=("Godot Validation",),
            merge_policy="squash with expected head",
            token_source="environment",
            rollback_procedure="disable scheduler and revoke token",
            emergency_stop_source="environment",
        )
        self.client = FakeClient()

    def tearDown(self):
        self.temp.cleanup()

    def transport(self, *, reviews=False, merges=False):
        return GuardedGitHubMutationTransport(
            self.store,
            self.client,
            ProductionMutationConfig(
                mode=SchedulerMode.PRODUCTION_GUARDED,
                manifest=self.manifest,
                reviews_enabled=reviews,
                merges_enabled=merges,
            ),
        )

    def command(self, kind, payload, operation="op-1"):
        return MutationCommand(
            operation_id=operation,
            kind=kind,
            repository=self.job.repository,
            payload={"job_id": self.job.job_id, **payload},
        )

    def test_requires_guarded_mode(self):
        with self.assertRaises(ValueError):
            ProductionMutationConfig(
                mode=SchedulerMode.DRY_RUN,
                manifest=self.manifest,
            ).validate()

    def test_allowlist_is_enforced(self):
        other = MutationCommand(
            operation_id="other",
            kind=MutationKind.CLAIM_ISSUE,
            repository=RepositoryTarget(owner="other", name="repo"),
            payload={"job_id": self.job.job_id, "issue_number": 1},
        )
        with self.assertRaises(GitHubAdapterError) as context:
            self.transport().execute(other)
        self.assertEqual(context.exception.kind, AdapterErrorKind.PERMISSION)

    def test_duplicate_operation_is_not_repeated(self):
        command = self.command(MutationKind.CLAIM_ISSUE, {"issue_number": 55})
        first = self.transport().execute(command)
        second = self.transport().execute(command)
        self.assertEqual(first, second)
        self.assertEqual(len(self.client.calls), 1)

    def test_reviews_require_separate_enablement_and_head_sha(self):
        command = self.command(
            MutationKind.SUBMIT_REVIEW,
            {"pull_request_number": 100, "event": "APPROVE", "reviewed_head_sha": "abc"},
        )
        with self.assertRaises(GitHubAdapterError):
            self.transport().execute(command)
        self.transport(reviews=True).execute(command)
        self.assertEqual(self.client.calls[-1][-1], "abc")

    def test_merges_require_enablement_and_expected_head(self):
        disabled = self.command(
            MutationKind.MERGE_PULL_REQUEST,
            {"pull_request_number": 100, "merge_method": "squash", "expected_head_sha": "abc"},
        )
        with self.assertRaises(GitHubAdapterError):
            self.transport().execute(disabled)
        missing_head = self.command(
            MutationKind.MERGE_PULL_REQUEST,
            {"pull_request_number": 100, "merge_method": "squash"},
            operation="merge-no-head",
        )
        with self.assertRaises(GitHubAdapterError) as context:
            self.transport(merges=True).execute(missing_head)
        self.assertEqual(context.exception.kind, AdapterErrorKind.CONFLICT)


if __name__ == "__main__":
    unittest.main()
