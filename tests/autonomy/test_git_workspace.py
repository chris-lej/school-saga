from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from autonomy.code_editing import CodeEditPlan, CodeEditingError, CodeEditingPolicy, FileChange
from autonomy.git_workspace import GitWorkspaceBackend


class GitWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-b", "main"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=self.root, check=True)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "fixture.md").write_text("before\n", encoding="utf-8")
        subprocess.run(["git", "add", "docs/fixture.md"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=self.root, check=True, capture_output=True)
        self.base_sha = self.git("rev-parse", "HEAD")
        self.policy = CodeEditingPolicy(
            repository_allowlist=("chris-lej/school-saga",),
            path_allowlist=("docs",),
            max_changed_files=2,
            max_patch_bytes=10_000,
        )

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.root, check=True, capture_output=True, text=True
        ).stdout.strip()

    def plan(self) -> CodeEditPlan:
        return CodeEditPlan(
            issue_number=59,
            branch="autonomy/issue-59",
            base_sha=self.base_sha,
            changes=(FileChange("docs/fixture.md", "after\n"),),
            commit_message="Update fixture",
            pull_request_title="Fixture",
        )

    def test_creates_real_commit_with_only_planned_file(self):
        result = GitWorkspaceBackend().apply(self.root, self.plan(), self.policy)
        self.assertEqual(result.commit_sha, self.git("rev-parse", "HEAD"))
        self.assertEqual(self.git("rev-parse", "HEAD^"), self.base_sha)
        self.assertEqual(self.git("show", "--pretty=", "--name-only", "HEAD"), "docs/fixture.md")
        self.assertEqual((self.root / "docs" / "fixture.md").read_text(), "after\n")

    def test_dirty_worktree_fails_closed(self):
        (self.root / "docs" / "fixture.md").write_text("dirty\n", encoding="utf-8")
        with self.assertRaises(CodeEditingError):
            GitWorkspaceBackend().apply(self.root, self.plan(), self.policy)

    def test_stale_base_fails_closed(self):
        plan = CodeEditPlan(
            issue_number=59,
            branch="autonomy/issue-59",
            base_sha="0" * 40,
            changes=(FileChange("docs/fixture.md", "after\n"),),
            commit_message="Update fixture",
            pull_request_title="Fixture",
        )
        with self.assertRaises(CodeEditingError):
            GitWorkspaceBackend().apply(self.root, plan, self.policy)

    def test_conflicting_existing_branch_fails_closed(self):
        subprocess.run(["git", "branch", "autonomy/issue-59"], cwd=self.root, check=True)
        (self.root / "other.txt").write_text("other\n", encoding="utf-8")
        subprocess.run(["git", "add", "other.txt"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "advance"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "branch", "-f", "autonomy/issue-59", "HEAD"], cwd=self.root, check=True)
        subprocess.run(["git", "checkout", "main"], cwd=self.root, check=True, capture_output=True)
        with self.assertRaises(CodeEditingError):
            GitWorkspaceBackend().apply(self.root, self.plan(), self.policy)


if __name__ == "__main__":
    unittest.main()
