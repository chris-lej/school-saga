from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from autonomy.code_editing import (
    CodeEditPlan,
    CodeEditingError,
    CodeEditingPolicy,
    FileChange,
    GuardedCodeEditingWorker,
    LocalWorkspaceBackend,
)
from autonomy.contracts import IssueWorkRequest, Job, JobState, RepositoryTarget
from autonomy.github_adapter import MutationResult
from autonomy.store import JsonJobStore
from autonomy.validation import ValidationCommand, ValidationService, ValidationStatus, ValidationStepResult


class PassingRunner:
    def run(self, command, *, cwd, environment, max_output_chars):
        return ValidationStepResult(command.name, ValidationStatus.PASSED, 0, stdout="ok")


class FailingRunner:
    def run(self, command, *, cwd, environment, max_output_chars):
        return ValidationStepResult(command.name, ValidationStatus.FAILED, 1, stderr="failed")


@dataclass
class FakeMutationExecutor:
    calls: list[str]

    def execute(self, command):
        self.calls.append(command.operation_id)
        details = {"result": {"number": 101}} if command.kind.value == "open_pull_request" else {"result": {}}
        return MutationResult(command.operation_id, command.kind, True, False, details)


class CodeEditingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.store = JsonJobStore(self.root / "jobs.json")
        self.job = Job(
            repository=RepositoryTarget(owner="chris-lej", name="school-saga"),
            request=IssueWorkRequest(issue_number=57, title="fixture"),
        )
        self.store.create(self.job, "create")
        self.store.transition(self.job.job_id, JobState.CLAIMED, "claim")
        self.policy = CodeEditingPolicy(
            repository_allowlist=("chris-lej/school-saga",),
            path_allowlist=("autonomy", "docs", "tests/autonomy"),
            max_changed_files=3,
            max_patch_bytes=200,
        )

    def tearDown(self):
        self.temp.cleanup()

    def plan(self, changes=None):
        return CodeEditPlan(
            issue_number=57,
            branch="autonomy/issue-57",
            base_sha="base123",
            changes=tuple(changes or (FileChange("docs/example.md", "hello\n"),)),
            commit_message="Implement fixture",
            pull_request_title="Fixture",
        )

    def worker(self, runner=None, enabled=True):
        validation = ValidationService(
            self.store,
            runner or PassingRunner(),
            commands=(ValidationCommand("fixture", ("fixture",)),),
            cwd=self.repo,
        )
        mutations = FakeMutationExecutor([])
        worker = GuardedCodeEditingWorker(
            self.store,
            LocalWorkspaceBackend(),
            validation,
            mutations,
            repository_root=self.repo,
            policy=self.policy,
            enabled=enabled,
        )
        return worker, mutations

    def test_guarded_worker_writes_allowed_file_and_opens_draft_pr_intent(self):
        worker, mutations = self.worker()
        result = worker.run(self.job.job_id, self.plan())
        self.assertEqual(result.state, JobState.VALIDATING)
        self.assertEqual(result.workspace.changed_files, ("docs/example.md",))
        self.assertTrue((self.repo / "docs/example.md").exists())
        self.assertEqual(result.worker_result.pull_request_number, 101)
        self.assertEqual(len(mutations.calls), 2)

    def test_disabled_worker_fails_closed(self):
        worker, _ = self.worker(enabled=False)
        with self.assertRaises(CodeEditingError):
            worker.run(self.job.job_id, self.plan())

    def test_path_traversal_is_rejected(self):
        worker, _ = self.worker()
        with self.assertRaises(CodeEditingError):
            worker.run(self.job.job_id, self.plan((FileChange("../escape.txt", "bad"),)))

    def test_disallowed_path_is_rejected(self):
        worker, _ = self.worker()
        with self.assertRaises(CodeEditingError):
            worker.run(self.job.job_id, self.plan((FileChange("project.godot", "bad"),)))

    def test_patch_size_limit_is_enforced(self):
        worker, _ = self.worker()
        with self.assertRaises(CodeEditingError):
            worker.run(self.job.job_id, self.plan((FileChange("docs/large.md", "x" * 201),)))

    def test_validation_failure_prevents_pr_creation(self):
        worker, mutations = self.worker(FailingRunner())
        with self.assertRaises(CodeEditingError):
            worker.run(self.job.job_id, self.plan())
        self.assertEqual(len(mutations.calls), 1)

    def test_restart_reuses_workspace_and_validation_operations(self):
        worker, mutations = self.worker()
        first = worker.run(self.job.job_id, self.plan())
        second = worker.run(self.job.job_id, self.plan())
        self.assertEqual(first.workspace, second.workspace)
        self.assertEqual(self.store.count_events(self.job.job_id, "worker.workspace.prepared"), 1)
        self.assertEqual(self.store.count_events(self.job.job_id, "worker.code_edit.completed"), 1)


if __name__ == "__main__":
    unittest.main()
