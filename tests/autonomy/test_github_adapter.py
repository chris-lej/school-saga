from __future__ import annotations

import unittest

from autonomy.contracts import RepositoryTarget
from autonomy.github_adapter import (
    AdapterErrorKind,
    DryRunMutationExecutor,
    GitHubAdapter,
    GitHubAdapterError,
    GuardedMutationExecutor,
    MutationCommand,
    MutationKind,
)


class FixtureTransport:
    def get_repository(self, repository):
        return {"owner": {"login": repository.owner}, "name": repository.name, "default_branch": "main"}

    def get_issue(self, repository, issue_number):
        return {
            "number": issue_number,
            "title": "Fixture issue",
            "body": "Fixture body",
            "state": "open",
            "labels": [{"name": "state:ready"}],
        }

    def get_pull_request(self, repository, pr_number):
        return {
            "number": pr_number,
            "state": "open",
            "draft": True,
            "head": {"ref": "feature", "sha": "abc123"},
            "base": {"ref": "main"},
        }

    def get_checks(self, repository, sha):
        return {"state": "success"}


class GitHubAdapterTests(unittest.TestCase):
    def setUp(self):
        self.target = RepositoryTarget(owner="chris-lej", name="school-saga")
        self.adapter = GitHubAdapter(FixtureTransport())

    def test_fixture_reads_map_to_contracts(self):
        issue = self.adapter.issue(self.target, 41)
        pull_request = self.adapter.pull_request(self.target, 42)
        checks = self.adapter.checks(self.target, pull_request.head_sha)

        self.assertEqual(issue.labels, ("state:ready",))
        self.assertTrue(pull_request.draft)
        self.assertTrue(checks.successful)

    def test_invalid_response_fails_closed(self):
        class InvalidTransport(FixtureTransport):
            def get_issue(self, repository, issue_number):
                return {"number": issue_number}

        with self.assertRaises(GitHubAdapterError) as context:
            GitHubAdapter(InvalidTransport()).issue(self.target, 41)
        self.assertEqual(context.exception.kind, AdapterErrorKind.INVALID_RESPONSE)

    def test_dry_run_is_idempotent_and_audited(self):
        executor = DryRunMutationExecutor()
        command = MutationCommand(
            operation_id="claim-41",
            kind=MutationKind.CLAIM_ISSUE,
            repository=self.target,
            payload={"issue_number": 41},
        )

        first = executor.execute("job-1", command)
        second = executor.execute("job-1", command)

        self.assertIs(first, second)
        self.assertFalse(first.executed)
        self.assertTrue(first.dry_run)
        self.assertEqual(len(executor.events()), 1)
        self.assertEqual(executor.events()[0].event_type, "github.mutation.dry_run")

    def test_guarded_executor_requires_explicit_enablement(self):
        executor = GuardedMutationExecutor()
        command = MutationCommand(
            operation_id="merge-42",
            kind=MutationKind.MERGE_PULL_REQUEST,
            repository=self.target,
            payload={"pull_request_number": 42},
        )
        with self.assertRaises(GitHubAdapterError) as context:
            executor.execute(command)
        self.assertEqual(context.exception.kind, AdapterErrorKind.PERMISSION)

    def test_enabled_mode_requires_transport(self):
        with self.assertRaises(ValueError):
            GuardedMutationExecutor(mutations_enabled=True)


if __name__ == "__main__":
    unittest.main()
