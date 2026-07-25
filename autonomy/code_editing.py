from __future__ import annotations

import hashlib
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Protocol

from .contracts import AuditEvent, JobState, WorkerResult, utc_now
from .github_adapter import MutationCommand, MutationKind, MutationResult
from .store import JsonJobStore
from .validation import ValidationRunResult, ValidationService


class CodeEditingError(RuntimeError):
    pass


@dataclass(frozen=True)
class FileChange:
    path: str
    content: str


@dataclass(frozen=True)
class CodeEditPlan:
    issue_number: int
    branch: str
    base_sha: str
    changes: tuple[FileChange, ...]
    commit_message: str
    pull_request_title: str
    pull_request_body: str = ""
    schema_version: int = 1


@dataclass(frozen=True)
class CodeEditingPolicy:
    repository_allowlist: tuple[str, ...]
    path_allowlist: tuple[str, ...]
    max_changed_files: int = 10
    max_patch_bytes: int = 100_000
    max_attempts: int = 2
    draft_pull_requests_only: bool = True

    def validate(self) -> None:
        if not self.repository_allowlist:
            raise ValueError("repository_allowlist cannot be empty")
        if not self.path_allowlist:
            raise ValueError("path_allowlist cannot be empty")
        if self.max_changed_files < 1:
            raise ValueError("max_changed_files must be positive")
        if self.max_patch_bytes < 1:
            raise ValueError("max_patch_bytes must be positive")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")


@dataclass(frozen=True)
class WorkspaceResult:
    workspace_id: str
    branch: str
    base_sha: str
    changed_files: tuple[str, ...]
    patch_sha256: str
    patch_bytes: int
    commit_sha: str


@dataclass(frozen=True)
class CodeEditingWorkerRunResult:
    job_id: str
    state: JobState
    workspace: WorkspaceResult
    validation: ValidationRunResult
    worker_result: WorkerResult
    branch_result: MutationResult
    pull_request_result: MutationResult


class CodeEditingBackend(Protocol):
    def apply(self, repository_root: Path, plan: CodeEditPlan, policy: CodeEditingPolicy) -> WorkspaceResult: ...


class MutationExecutor(Protocol):
    def execute(self, command: MutationCommand) -> MutationResult: ...


class LocalWorkspaceBackend:
    """Bounded local workspace editor with path and symlink escape protection."""

    @staticmethod
    def _normalized_path(path: str) -> PurePosixPath:
        candidate = PurePosixPath(path)
        if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
            raise CodeEditingError(f"Unsafe repository path: {path!r}")
        return candidate

    @staticmethod
    def _path_allowed(path: PurePosixPath, allowlist: tuple[str, ...]) -> bool:
        normalized = path.as_posix()
        return any(normalized == prefix.rstrip("/") or normalized.startswith(prefix.rstrip("/") + "/") for prefix in allowlist)

    def apply(self, repository_root: Path, plan: CodeEditPlan, policy: CodeEditingPolicy) -> WorkspaceResult:
        policy.validate()
        root = repository_root.resolve()
        if not root.is_dir():
            raise CodeEditingError(f"Repository workspace does not exist: {root}")
        if len(plan.changes) > policy.max_changed_files:
            raise CodeEditingError("Change plan exceeds maximum changed-file count")

        total_bytes = sum(len(change.content.encode("utf-8")) for change in plan.changes)
        if total_bytes > policy.max_patch_bytes:
            raise CodeEditingError("Change plan exceeds maximum patch size")

        normalized_changes: list[tuple[Path, FileChange]] = []
        for change in plan.changes:
            relative = self._normalized_path(change.path)
            if not self._path_allowed(relative, policy.path_allowlist):
                raise CodeEditingError(f"Path is not allowlisted: {change.path}")
            target = root.joinpath(*relative.parts)
            parent = target.parent
            parent.mkdir(parents=True, exist_ok=True)
            resolved_parent = parent.resolve()
            if root != resolved_parent and root not in resolved_parent.parents:
                raise CodeEditingError(f"Path escapes repository workspace: {change.path}")
            if target.exists() and target.is_symlink():
                raise CodeEditingError(f"Refusing to overwrite symlink: {change.path}")
            normalized_changes.append((target, change))

        digest = hashlib.sha256()
        for target, change in normalized_changes:
            target.write_text(change.content, encoding="utf-8")
            digest.update(change.path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(change.content.encode("utf-8"))
            digest.update(b"\0")

        patch_sha = digest.hexdigest()
        workspace_id = hashlib.sha256(f"{root}:{plan.branch}:{plan.base_sha}".encode("utf-8")).hexdigest()[:24]
        commit_sha = hashlib.sha256(
            f"{plan.base_sha}:{plan.branch}:{plan.commit_message}:{patch_sha}".encode("utf-8")
        ).hexdigest()
        return WorkspaceResult(
            workspace_id=workspace_id,
            branch=plan.branch,
            base_sha=plan.base_sha,
            changed_files=tuple(change.path for change in plan.changes),
            patch_sha256=patch_sha,
            patch_bytes=total_bytes,
            commit_sha=commit_sha,
        )


class GuardedCodeEditingWorker:
    """Explicitly enabled Worker that edits an allowlisted local workspace and opens only draft PRs."""

    def __init__(
        self,
        store: JsonJobStore,
        backend: CodeEditingBackend,
        validation: ValidationService,
        mutations: MutationExecutor,
        *,
        repository_root: str | Path,
        policy: CodeEditingPolicy,
        enabled: bool = False,
    ):
        policy.validate()
        self.store = store
        self.backend = backend
        self.validation = validation
        self.mutations = mutations
        self.repository_root = Path(repository_root)
        self.policy = policy
        self.enabled = enabled

    @staticmethod
    def _operation(job_id: str, action: str) -> str:
        return f"{job_id}:code-edit-worker:{action}"

    def _persist(self, job_id: str, operation_id: str, payload: dict, event_type: str) -> dict:
        existing = self.store.get_operation_result(operation_id)
        if existing is not None:
            return existing
        event = AuditEvent(
            event_id=f"{job_id}:{event_type}:{operation_id}",
            job_id=job_id,
            operation_id=operation_id,
            event_type=event_type,
            timestamp=utc_now(),
            details=payload,
        )
        return self.store.record_operation_result(job_id, operation_id, payload, event)

    def run(self, job_id: str, plan: CodeEditPlan) -> CodeEditingWorkerRunResult:
        if not self.enabled:
            raise CodeEditingError("Guarded code-editing Worker is disabled")
        job = self.store.get(job_id)
        repository_name = f"{job.repository.owner}/{job.repository.name}"
        if repository_name not in self.policy.repository_allowlist:
            raise CodeEditingError(f"Repository is not allowlisted: {repository_name}")
        if job.state not in {JobState.CLAIMED, JobState.EXECUTING}:
            raise CodeEditingError(f"Code-editing Worker does not own state {job.state.value!r}")
        if job.attempts >= self.policy.max_attempts and job.state == JobState.CLAIMED:
            raise CodeEditingError("Maximum Worker attempts exceeded")
        if plan.issue_number != job.request.issue_number:
            raise CodeEditingError("Plan issue number does not match persisted job")
        if self.policy.draft_pull_requests_only is not True:
            raise CodeEditingError("Production code editing requires draft_pull_requests_only")

        if job.state == JobState.CLAIMED:
            self.store.transition(job_id, JobState.EXECUTING, self._operation(job_id, "execute"))

        workspace_operation = self._operation(job_id, "workspace")
        existing_workspace = self.store.get_operation_result(workspace_operation)
        if existing_workspace is None:
            workspace = self.backend.apply(self.repository_root, plan, self.policy)
            self._persist(job_id, workspace_operation, asdict(workspace), "worker.workspace.prepared")
        else:
            workspace = WorkspaceResult(**existing_workspace)

        branch_command = MutationCommand(
            operation_id=self._operation(job_id, "github-branch"),
            kind=MutationKind.CREATE_BRANCH,
            repository=job.repository,
            payload={
                "job_id": job_id,
                "branch": plan.branch,
                "base": job.repository.default_branch,
                "expected_base_sha": plan.base_sha,
            },
        )
        branch_result = self.mutations.execute(branch_command)

        if self.store.get(job_id).state == JobState.EXECUTING:
            self.store.transition(job_id, JobState.VALIDATING, self._operation(job_id, "validate"))
        validation = self.validation.validate(job_id, self._operation(job_id, "validation"))
        if not validation.passed:
            raise CodeEditingError(f"Validation failed with status {validation.status.value}")

        pr_command = MutationCommand(
            operation_id=self._operation(job_id, "github-pr"),
            kind=MutationKind.OPEN_PULL_REQUEST,
            repository=job.repository,
            payload={
                "job_id": job_id,
                "issue_number": plan.issue_number,
                "title": plan.pull_request_title,
                "body": plan.pull_request_body,
                "head": plan.branch,
                "base": job.repository.default_branch,
                "draft": True,
                "expected_head_sha": workspace.commit_sha,
            },
        )
        pull_request_result = self.mutations.execute(pr_command)
        worker_result = WorkerResult(
            branch=plan.branch,
            commit_sha=workspace.commit_sha,
            pull_request_number=pull_request_result.details.get("result", {}).get("number"),
            summary=f"Guarded Worker changed {len(workspace.changed_files)} file(s) and passed validation",
        )
        self._persist(
            job_id,
            self._operation(job_id, "result"),
            {
                "worker_result": asdict(worker_result),
                "workspace": asdict(workspace),
                "validation_operation_id": validation.operation_id,
                "validation_status": validation.status.value,
                "branch_operation_id": branch_command.operation_id,
                "pull_request_operation_id": pr_command.operation_id,
            },
            "worker.code_edit.completed",
        )
        return CodeEditingWorkerRunResult(
            job_id=job_id,
            state=self.store.get(job_id).state,
            workspace=workspace,
            validation=validation,
            worker_result=worker_result,
            branch_result=branch_result,
            pull_request_result=pull_request_result,
        )
