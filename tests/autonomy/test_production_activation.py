from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from autonomy.code_editing import CodeEditPlan, CodeEditingWorkerRunResult, FileChange, WorkspaceResult
from autonomy.contracts import IssueWorkRequest, Job, JobState, RepositoryTarget, WorkerResult
from autonomy.github_adapter import MutationKind, MutationResult
from autonomy.production_activation import (
    ActivationGate,
    ActivationStatus,
    GuardedProductionActivation,
    ProductionActivationConfig,
    ProductionActivationError,
    StaticProductionPreflight,
)
from autonomy.rehearsal import StaticEmergencyStop
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
            workspace_id="workspace",
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
            pull_request_number=123,
            summary="fixture",
        )
        mutation = MutationResult(
            operation_id="fixture",
            kind=MutationKind.OPEN_PULL_REQUEST,
            executed=True,
            dry_run=False,
            details={"result": {"number": 123}},
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
        self.root = Path(self.temp.name)
        self.store = JsonJobStore(self.root / "jobs.json")
        self.job = Job(
            repository=RepositoryTarget(owner="chris-lej", name="school-saga"),
            request=IssueWorkRequest(issue_number=66, title="fixture"),
        )
        self.store.create(self.job, "create")
        self.store.transition(self.job.job_id, JobState.CLAIMED, "claim")
        self.worker = FixtureWorker()
        self.config = ProductionActivationConfig(
            repository="chris-lej/school-saga",
            repository_root=str(self.root),
            expected_default_branch_sha="base-sha",
            issue_label_allowlist=("state:ready",),
            path_allowlist=("docs",),
            validation_command_allowlist=("bash scripts/validate-pr.sh",),
            mutation_allowlist=("claim_issue", "create_branch", "open_pull_request"),
            token_source="environment",
            rollback_procedure="disable activation and remove branch",
            emergency_stop_source="environment",
            required_checks=("Godot Validation",),
            production_development_enabled=True,
        )
        self.plan = CodeEditPlan(
            issue_number=66,
            branch="autonomy/issue-66",
            base_sha="base-sha",
            changes=(FileChange("docs/fixture.md", "fixture\n"),),
            commit_message="Fixture",
            pull_request_title="Fixture",
        )

    def tearDown(self):
        self.temp.cleanup()

    def activation(self, *, stop=False, gates=()):
        return GuardedProductionActivation(
            self.store,
            self.worker,
            StaticProductionPreflight(gates),
            StaticEmergencyStop(stop),
            self.config,
        )

    def test_success_creates_draft_pr_report(self):
        report = self.activation().run_one(self.job.job_id, self.plan)
        self.assertEqual(report.status, ActivationStatus.DRAFT_PR_CREATED)
        self.assertEqual(report.pull_request_number, 123)
        self.assertIn("production_merge", report.disabled_capabilities)

    def test_completed_run_is_idempotent(self):
        first = self.activation().run_one(self.job.job_id, self.plan)
        second = self.activation().run_one(self.job.job_id, self.plan)
        self.assertEqual(first, second)
        self.assertEqual(self.worker.calls, 1)

    def test_emergency_stop_halts_before_worker(self):
        report = self.activation(stop=True).run_one(self.job.job_id, self.plan)
        self.assertEqual(report.status, ActivationStatus.HALTED)
        self.assertEqual(self.worker.calls, 0)

    def test_failed_preflight_fails_closed(self):
        report = self.activation(gates=(ActivationGate("permissions", False, "missing"),)).run_one(
            self.job.job_id, self.plan
        )
        self.assertEqual(report.status, ActivationStatus.FAILED)
        self.assertEqual(self.worker.calls, 0)

    def test_repository_mismatch_is_rejected(self):
        config = ProductionActivationConfig(
            **{**self.config.__dict__, "repository": "other/repository"}
        )
        activation = GuardedProductionActivation(
            self.store,
            self.worker,
            StaticProductionPreflight(),
            StaticEmergencyStop(False),
            config,
        )
        with self.assertRaises(ProductionActivationError):
            activation.run_one(self.job.job_id, self.plan)

    def test_high_risk_capabilities_cannot_be_enabled(self):
        with self.assertRaises(ValueError):
            ProductionActivationConfig(
                **{**self.config.__dict__, "merges_enabled": True}
            ).validate()


if __name__ == "__main__":
    unittest.main()
