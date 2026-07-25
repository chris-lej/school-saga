from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from autonomy.code_editing import CodeEditPlan, CodeEditingWorkerRunResult, FileChange, WorkspaceResult
from autonomy.contracts import IssueWorkRequest, Job, JobState, RepositoryTarget, WorkerResult
from autonomy.github_adapter import MutationKind, MutationResult
from autonomy.rehearsal import GuardedRehearsalRunner, RehearsalError, RehearsalStatus, StaticEmergencyStop
from autonomy.store import JsonJobStore
from autonomy.validation import ValidationRunResult, ValidationStatus


@dataclass
class FixtureWorker:
    calls: int = 0
    fail: bool = False

    def run(self, job_id: str, plan: CodeEditPlan) -> CodeEditingWorkerRunResult:
        self.calls += 1
        if self.fail:
            raise RuntimeError("fixture failure")
        validation = ValidationRunResult(
            operation_id=f"{job_id}:validation",
            attempt=1,
            status=ValidationStatus.PASSED,
        )
        workspace = WorkspaceResult(
            workspace_id="fixture-workspace",
            branch=plan.branch,
            base_sha=plan.base_sha,
            changed_files=tuple(change.path for change in plan.changes),
            patch_sha256="patch-sha",
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


class RehearsalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = JsonJobStore(Path(self.temp.name) / "jobs.json")
        self.job = Job(
            repository=RepositoryTarget(owner="fixture", name="rehearsal-repo"),
            request=IssueWorkRequest(issue_number=61, title="Rehearsal fixture"),
        )
        self.store.create(self.job, "create-job")
        self.store.transition(self.job.job_id, JobState.CLAIMED, "claim")
        self.plan = CodeEditPlan(
            issue_number=61,
            branch="autonomy/issue-61",
            base_sha="base123",
            changes=(FileChange("docs/fixture.md", "fixture\n"),),
            commit_message="Rehearsal fixture",
            pull_request_title="Rehearsal fixture",
        )

    def tearDown(self):
        self.temp.cleanup()

    def runner(self, worker=None, stop=None, allowlist=("fixture/rehearsal-repo",)):
        return GuardedRehearsalRunner(
            self.store,
            worker or FixtureWorker(),
            stop or StaticEmergencyStop(False),
            isolated_repository_allowlist=allowlist,
        )

    def test_success_persists_draft_pr_report(self):
        worker = FixtureWorker()
        runner = self.runner(worker=worker)
        first = runner.run_to_draft_pr(self.job.job_id, self.plan)
        second = runner.run_to_draft_pr(self.job.job_id, self.plan)
        self.assertEqual(first.status, RehearsalStatus.DRAFT_PR_CREATED)
        self.assertEqual(first.pull_request_number, 101)
        self.assertEqual(first, second)
        self.assertEqual(worker.calls, 1)
        self.assertEqual(self.store.count_events(self.job.job_id, "rehearsal.completed"), 1)

    def test_emergency_stop_halts_without_worker_call(self):
        worker = FixtureWorker()
        report = self.runner(worker=worker, stop=StaticEmergencyStop(True)).run_to_draft_pr(
            self.job.job_id, self.plan
        )
        self.assertEqual(report.status, RehearsalStatus.HALTED)
        self.assertEqual(worker.calls, 0)

    def test_allowlist_mismatch_fails_closed(self):
        with self.assertRaises(RehearsalError):
            self.runner(allowlist=("other/repo",)).run_to_draft_pr(self.job.job_id, self.plan)

    def test_worker_failure_is_persisted(self):
        worker = FixtureWorker(fail=True)
        report = self.runner(worker=worker).run_to_draft_pr(self.job.job_id, self.plan)
        self.assertEqual(report.status, RehearsalStatus.FAILED)
        self.assertEqual(worker.calls, 1)
        self.assertEqual(self.store.count_events(self.job.job_id, "rehearsal.failed"), 1)


if __name__ == "__main__":
    unittest.main()
