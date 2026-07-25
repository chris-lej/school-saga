from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from autonomy.code_editing import CodeEditPlan, CodeEditingWorkerRunResult, FileChange, WorkspaceResult
from autonomy.contracts import IssueWorkRequest, Job, JobState, RepositoryTarget, WorkerResult
from autonomy.github_adapter import MutationKind, MutationResult
from autonomy.production_worker import (
    GuardedProductionWorkerRunner,
    ProductionWorkerActivationError,
    ProductionWorkerManifest,
)
from autonomy.store import JsonJobStore
from autonomy.validation import ValidationRunResult, ValidationStatus


@dataclass
class FixtureStop:
    stopped: bool = False

    def active(self) -> bool:
        return self.stopped


@dataclass
class FixtureWorker:
    calls: int = 0

    def run(self, job_id: str, plan: CodeEditPlan) -> CodeEditingWorkerRunResult:
        self.calls += 1
        validation = ValidationRunResult(
            operation_id=f"{job_id}:validation",
            attempt=1,
            status=ValidationStatus.PASSED,
        )
        workspace = WorkspaceResult(
            workspace_id="workspace-1",
            branch=plan.branch,
            base_sha=plan.base_sha,
            changed_files=("docs/fixture.md",),
            patch_sha256="patch",
            patch_bytes=10,
            commit_sha="abc123",
        )
        worker_result = WorkerResult(
            branch=plan.branch,
            commit_sha="abc123",
            pull_request_number=101,
            summary="fixture",
        )
        mutation = MutationResult(
            operation_id="fixture",
            kind=MutationKind.OPEN_PULL_REQUEST,
            executed=True,
            dry_run=False,
            details={"result": {"number": 101}},
        )
        return CodeEditingWorkerRunResult(
            job_id=job_id,
            state=JobState.VALIDATING,
            workspace=workspace,
            validation=validation,
            worker_result=worker_result,
            branch_result=mutation,
            pull_request_result=mutation,
        )


class ProductionWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = JsonJobStore(Path(self.temp.name) / "jobs.json")
        self.job = Job(
            job_id="job-70",
            repository=RepositoryTarget(owner="chris-lej", name="school-saga"),
            request=IssueWorkRequest(issue_number=70, title="fixture", body="fixture"),
            state=JobState.CLAIMED,
        )
        self.store.create(self.job)
        self.worker = FixtureWorker()
        self.stop = FixtureStop()
        self.manifest = ProductionWorkerManifest(
            repository_allowlist=("chris-lej/school-saga",),
            path_allowlist=("docs", "autonomy", "tests/autonomy"),
            command_allowlist=("python -m unittest", "bash scripts/validate-pr.sh"),
            mutation_allowlist=("create_branch", "open_pull_request"),
            required_token_scopes=("contents:write", "pull_requests:write", "issues:write"),
        )
        self.plan = CodeEditPlan(
            issue_number=70,
            branch="autonomy/issue-70",
            base_sha="base-sha",
            changes=(FileChange("docs/fixture.md", "after\n"),),
            commit_message="Update fixture",
            pull_request_title="Fixture",
        )

    def tearDown(self):
        self.temp.cleanup()

    def runner(self, *, enabled: bool = True):
        return GuardedProductionWorkerRunner(
            self.store,
            self.worker,
            self.stop,
            manifest=self.manifest,
            enabled=enabled,
        )

    def test_selected_issue_reaches_draft_pr_and_is_idempotent(self):
        first = self.runner().run_selected_issue("job-70", 70, self.plan)
        second = self.runner().run_selected_issue("job-70", 70, self.plan)
        self.assertEqual(first.status, "draft_pr_created")
        self.assertEqual(first.pull_request_number, 101)
        self.assertEqual(first.local_commit_sha, "abc123")
        self.assertEqual(first, second)
        self.assertEqual(self.worker.calls, 1)

    def test_disabled_activation_fails_closed(self):
        with self.assertRaises(ProductionWorkerActivationError):
            self.runner(enabled=False).run_selected_issue("job-70", 70, self.plan)

    def test_emergency_stop_fails_before_worker(self):
        self.stop.stopped = True
        with self.assertRaises(ProductionWorkerActivationError):
            self.runner().run_selected_issue("job-70", 70, self.plan)
        self.assertEqual(self.worker.calls, 0)

    def test_issue_mismatch_fails_closed(self):
        with self.assertRaises(ProductionWorkerActivationError):
            self.runner().run_selected_issue("job-70", 71, self.plan)

    def test_incomplete_manifest_fails_closed(self):
        with self.assertRaises(ProductionWorkerActivationError):
            ProductionWorkerManifest(
                repository_allowlist=("chris-lej/school-saga",),
                path_allowlist=(),
                command_allowlist=("validate",),
                mutation_allowlist=("create_branch",),
                required_token_scopes=("contents:write",),
            ).validate()


if __name__ == "__main__":
    unittest.main()
