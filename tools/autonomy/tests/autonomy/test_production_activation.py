from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from autonomy.code_editing import CodeEditPlan, CodeEditingWorkerRunResult, FileChange, WorkspaceResult
from autonomy.contracts import IssueWorkRequest, Job, JobState, RepositoryTarget, WorkerResult
from autonomy.github_adapter import MutationKind, MutationResult
from autonomy.production_activation import (
    ActivationStatus,
    DefaultActivationPreflight,
    ProductionActivationError,
    ProductionDevelopmentConfig,
    ProductionDevelopmentController,
)
from autonomy.rehearsal import StaticEmergencyStop
from autonomy.scheduler import ProductionReadinessManifest, SchedulerMode
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
            workspace_id="production-fixture",
            branch=plan.branch,
            base_sha=plan.base_sha,
            changed_files=tuple(change.path for change in plan.changes),
            patch_sha256="patch",
            patch_bytes=10,
            commit_sha="abc123",
        )
        worker_result = WorkerResult(
            branch=plan.branch,
            commit_sha="abc123",
            pull_request_number=202,
            summary="fixture",
        )
        mutation = MutationResult(
            operation_id="fixture",
            kind=MutationKind.OPEN_PULL_REQUEST,
            executed=True,
            dry_run=False,
            details={"result": {"number": 202}},
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


class ProductionActivationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = JsonJobStore(Path(self.temp.name) / "jobs.json")
        self.job = Job(
            repository=RepositoryTarget(owner="chris-lej", name="school-saga"),
            request=IssueWorkRequest(issue_number=68, title="fixture"),
            state=JobState.CLAIMED,
        )
        self.store.create(self.job, "create")
        self.manifest = ProductionReadinessManifest(
            repository_allowlist=("chris-lej/school-saga",),
            permitted_mutation_kinds=("claim_issue", "create_branch", "open_pull_request"),
            required_checks=("Godot Validation",),
            merge_policy="disabled",
            token_source="environment",
            rollback_procedure="disable activation and revoke token",
            emergency_stop_source="environment",
        )
        self.config = ProductionDevelopmentConfig(
            mode=SchedulerMode.PRODUCTION_GUARDED,
            repository="chris-lej/school-saga",
            manifest=self.manifest,
            path_allowlist=("docs", "game", "tools"),
            command_allowlist=("bash scripts/validate-pr.sh",),
        )
        self.plan = CodeEditPlan(
            issue_number=68,
            branch="autonomy/issue-68",
            base_sha="base123",
            changes=(FileChange("docs/fixture.md", "after\n"),),
            commit_message="Update fixture",
            pull_request_title="Fixture",
        )

    def tearDown(self):
        self.temp.cleanup()

    def controller(self, worker=None, stop=False, config=None):
        return ProductionDevelopmentController(
            self.store,
            worker or FixtureWorker(),
            StaticEmergencyStop(stop),
            config or self.config,
        )

    def test_success_creates_machine_readable_report(self):
        worker = FixtureWorker()
        controller = self.controller(worker)
        report = controller.run_single_cycle(self.job.job_id, self.plan)
        self.assertEqual(report.status, ActivationStatus.DRAFT_PR_CREATED)
        self.assertEqual(report.head_sha, "abc123")
        self.assertEqual(report.pull_request_number, 202)
        self.assertEqual(worker.calls, 1)

    def test_restart_returns_persisted_result(self):
        worker = FixtureWorker()
        controller = self.controller(worker)
        first = controller.run_single_cycle(self.job.job_id, self.plan)
        second = controller.run_single_cycle(self.job.job_id, self.plan)
        self.assertEqual(first, second)
        self.assertEqual(worker.calls, 1)

    def test_emergency_stop_halts_before_worker(self):
        worker = FixtureWorker()
        report = self.controller(worker, stop=True).run_single_cycle(self.job.job_id, self.plan)
        self.assertEqual(report.status, ActivationStatus.HALTED)
        self.assertEqual(worker.calls, 0)

    def test_forbidden_mutation_fails_closed(self):
        unsafe_manifest = ProductionReadinessManifest(
            repository_allowlist=("chris-lej/school-saga",),
            permitted_mutation_kinds=("claim_issue", "create_branch", "open_pull_request", "merge_pull_request"),
            required_checks=("Godot Validation",),
            merge_policy="disabled",
            token_source="environment",
            rollback_procedure="disable activation and revoke token",
            emergency_stop_source="environment",
        )
        unsafe = ProductionDevelopmentConfig(
            mode=SchedulerMode.PRODUCTION_GUARDED,
            repository="chris-lej/school-saga",
            manifest=unsafe_manifest,
            path_allowlist=("docs",),
            command_allowlist=("bash scripts/validate-pr.sh",),
        )
        with self.assertRaises(ProductionActivationError):
            DefaultActivationPreflight().validate(unsafe)

    def test_review_and_merge_cannot_be_enabled(self):
        unsafe = ProductionDevelopmentConfig(
            mode=SchedulerMode.PRODUCTION_GUARDED,
            repository="chris-lej/school-saga",
            manifest=self.manifest,
            path_allowlist=("docs",),
            command_allowlist=("bash scripts/validate-pr.sh",),
            review_enabled=True,
        )
        with self.assertRaises(ProductionActivationError):
            unsafe.validate()


if __name__ == "__main__":
    unittest.main()
