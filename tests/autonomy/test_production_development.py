from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from autonomy.code_editing import CodeEditPlan, CodeEditingWorkerRunResult, FileChange, WorkspaceResult
from autonomy.contracts import IssueWorkRequest, Job, JobState, RepositoryTarget, WorkerResult
from autonomy.github_adapter import MutationKind, MutationResult
from autonomy.rehearsal import StaticEmergencyStop
from autonomy.scheduler import ProductionReadinessManifest
from autonomy.store import JsonJobStore
from autonomy.validation import ValidationRunResult, ValidationStatus
from scripts.autonomy.production_development import (
    GuardedProductionDevelopmentRunner,
    ProductionDevelopmentConfig,
    ProductionDevelopmentStatus,
)


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
            pull_request_number=201,
            summary="fixture",
        )
        mutation = MutationResult(
            operation_id="fixture",
            kind=MutationKind.OPEN_PULL_REQUEST,
            executed=True,
            dry_run=False,
            details={"result": {"number": 201}},
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


class ProductionDevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = JsonJobStore(self.root / "jobs.json")
        self.job = Job(
            repository=RepositoryTarget(owner="chris-lej", name="school-saga"),
            request=IssueWorkRequest(issue_number=64, title="fixture"),
        )
        self.store.create(self.job, "create-job")
        self.store.transition(self.job.job_id, JobState.CLAIMED, "claim-job")
        self.manifest = ProductionReadinessManifest(
            repository_allowlist=("chris-lej/school-saga",),
            permitted_mutation_kinds=("claim_issue", "create_branch", "open_pull_request"),
            required_checks=("Godot Validation",),
            merge_policy="draft PR only; human merge",
            token_source="environment",
            rollback_procedure="stop runner, revoke token, delete branch after inspection",
            emergency_stop_source="environment",
        )
        self.worker = FixtureWorker()

    def tearDown(self):
        self.temp.cleanup()

    def config(self, **overrides):
        values = {
            "enabled": True,
            "repository": "chris-lej/school-saga",
            "repository_root": str(self.root),
            "readiness_manifest": self.manifest,
        }
        values.update(overrides)
        return ProductionDevelopmentConfig(**values)

    def runner(self, stop=False, config=None):
        return GuardedProductionDevelopmentRunner(
            self.store,
            self.worker,
            StaticEmergencyStop(stop),
            config or self.config(),
        )

    def plan(self):
        return CodeEditPlan(
            issue_number=64,
            branch="autonomy/issue-64",
            base_sha="base-sha",
            changes=(FileChange("docs/fixture.md", "fixture\n"),),
            commit_message="Fixture change",
            pull_request_title="Fixture draft PR",
        )

    def test_success_records_draft_pr_and_disabled_gates(self):
        report = self.runner().run_to_draft_pr(self.job.job_id, self.plan())
        self.assertEqual(report.status, ProductionDevelopmentStatus.DRAFT_PR_CREATED)
        self.assertEqual(report.local_commit_sha, "abc123")
        self.assertEqual(report.pull_request_number, 201)
        self.assertIn("production_review_disabled", report.unresolved_production_gates)
        self.assertIn("production_merge_disabled", report.unresolved_production_gates)

    def test_restart_returns_persisted_report(self):
        runner = self.runner()
        first = runner.run_to_draft_pr(self.job.job_id, self.plan())
        second = runner.run_to_draft_pr(self.job.job_id, self.plan())
        self.assertEqual(first, second)
        self.assertEqual(self.worker.calls, 1)

    def test_emergency_stop_halts_before_worker(self):
        report = self.runner(stop=True).run_to_draft_pr(self.job.job_id, self.plan())
        self.assertEqual(report.status, ProductionDevelopmentStatus.HALTED)
        self.assertEqual(self.worker.calls, 0)

    def test_branch_prefix_fails_closed(self):
        plan = CodeEditPlan(
            issue_number=64,
            branch="feature/unsafe",
            base_sha="base-sha",
            changes=(FileChange("docs/fixture.md", "fixture\n"),),
            commit_message="Fixture change",
            pull_request_title="Fixture draft PR",
        )
        report = self.runner().run_to_draft_pr(self.job.job_id, plan)
        self.assertEqual(report.status, ProductionDevelopmentStatus.FAILED)
        self.assertEqual(self.worker.calls, 0)

    def test_review_or_merge_enablement_is_rejected(self):
        with self.assertRaises(ValueError):
            self.config(reviews_enabled=True).validate()
        with self.assertRaises(ValueError):
            self.config(merges_enabled=True).validate()

    def test_worker_failure_is_reported(self):
        self.worker.fail = True
        report = self.runner().run_to_draft_pr(self.job.job_id, self.plan())
        self.assertEqual(report.status, ProductionDevelopmentStatus.FAILED)
        self.assertTrue(any(gate.name == "guarded_worker" and not gate.passed for gate in report.gates))


if __name__ == "__main__":
    unittest.main()
