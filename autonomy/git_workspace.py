from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .code_editing import (
    CodeEditPlan,
    CodeEditingError,
    CodeEditingPolicy,
    LocalWorkspaceBackend,
    WorkspaceResult,
)


@dataclass(frozen=True)
class GitCommandResult:
    stdout: str
    stderr: str


class GitWorkspaceBackend(LocalWorkspaceBackend):
    """Real local Git backend with stale-base, dirty-tree, and staging guards."""

    def __init__(self, *, author_name: str = "School Saga Autonomy", author_email: str = "autonomy@localhost"):
        self.author_name = author_name
        self.author_email = author_email

    @staticmethod
    def _git(root: Path, *args: str, env: dict[str, str] | None = None) -> GitCommandResult:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or f"git {' '.join(args)} failed"
            raise CodeEditingError(message)
        return GitCommandResult(completed.stdout.strip(), completed.stderr.strip())

    def apply(self, repository_root: Path, plan: CodeEditPlan, policy: CodeEditingPolicy) -> WorkspaceResult:
        policy.validate()
        root = repository_root.resolve()
        if not root.is_dir():
            raise CodeEditingError(f"Repository workspace does not exist: {root}")

        git_dir = self._git(root, "rev-parse", "--git-dir").stdout
        if not git_dir:
            raise CodeEditingError("Repository root is not a Git worktree")

        actual_base = self._git(root, "rev-parse", plan.base_sha).stdout
        if actual_base != plan.base_sha:
            raise CodeEditingError("Configured base SHA does not resolve exactly")

        status = self._git(root, "status", "--porcelain", "--untracked-files=all").stdout
        if status:
            raise CodeEditingError("Git worktree must be clean before guarded editing")

        existing_branch = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{plan.branch}"],
            cwd=root,
            check=False,
        ).returncode == 0
        if existing_branch:
            branch_sha = self._git(root, "rev-parse", plan.branch).stdout
            if branch_sha != plan.base_sha:
                raise CodeEditingError("Existing issue branch does not point at the expected base SHA")
            self._git(root, "checkout", plan.branch)
        else:
            self._git(root, "checkout", "-b", plan.branch, plan.base_sha)

        workspace = super().apply(root, plan, policy)

        for change in plan.changes:
            relative = self._normalized_path(change.path)
            mode = self._git(root, "ls-files", "-s", "--", relative.as_posix()).stdout
            if mode and mode.split()[0] == "160000":
                raise CodeEditingError(f"Refusing to edit submodule path: {change.path}")

        planned = tuple(change.path for change in plan.changes)
        self._git(root, "add", "--", *planned)
        staged = tuple(
            line
            for line in self._git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR").stdout.splitlines()
            if line
        )
        if tuple(sorted(staged)) != tuple(sorted(planned)):
            raise CodeEditingError("Staged paths differ from the declared change plan")

        patch = self._git(root, "diff", "--cached", "--binary", "--", *planned).stdout.encode("utf-8")
        patch_sha = hashlib.sha256(patch).hexdigest()
        if len(patch) > policy.max_patch_bytes:
            raise CodeEditingError("Staged patch exceeds maximum patch size")

        tree_sha = self._git(root, "write-tree").stdout
        env = dict(os.environ)
        env.update(
            {
                "GIT_AUTHOR_NAME": self.author_name,
                "GIT_AUTHOR_EMAIL": self.author_email,
                "GIT_COMMITTER_NAME": self.author_name,
                "GIT_COMMITTER_EMAIL": self.author_email,
            }
        )
        self._git(root, "commit", "-m", plan.commit_message, env=env)
        commit_sha = self._git(root, "rev-parse", "HEAD").stdout
        if self._git(root, "rev-parse", "HEAD^").stdout != plan.base_sha:
            raise CodeEditingError("Created commit is not based on the expected base SHA")

        workspace_id = hashlib.sha256(f"{root}:{plan.branch}:{plan.base_sha}".encode("utf-8")).hexdigest()[:24]
        return WorkspaceResult(
            workspace_id=workspace_id,
            branch=plan.branch,
            base_sha=plan.base_sha,
            changed_files=planned,
            patch_sha256=patch_sha,
            patch_bytes=len(patch),
            commit_sha=commit_sha,
        )
