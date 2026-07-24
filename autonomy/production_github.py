from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol

from .github_adapter import (
    AdapterErrorKind,
    GitHubAdapterError,
    MutationCommand,
    MutationKind,
    MutationResult,
)
from .scheduler import ProductionReadinessManifest, SchedulerMode
from .store import JsonJobStore


class GitHubMutationClient(Protocol):
    def claim_issue(self, repository: str, issue_number: int) -> dict[str, Any]: ...

    def create_branch(self, repository: str, branch: str, base: str) -> dict[str, Any]: ...

    def open_pull_request(
        self,
        repository: str,
        *,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> dict[str, Any]: ...

    def submit_review(
        self,
        repository: str,
        *,
        pull_request_number: int,
        event: str,
        reviewed_head_sha: str,
    ) -> dict[str, Any]: ...

    def merge_pull_request(
        self,
        repository: str,
        *,
        pull_request_number: int,
        merge_method: str,
        expected_head_sha: str,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ProductionMutationConfig:
    mode: SchedulerMode
    manifest: ProductionReadinessManifest
    reviews_enabled: bool = False
    merges_enabled: bool = False

    def validate(self) -> None:
        if self.mode != SchedulerMode.PRODUCTION_GUARDED:
            raise ValueError("Production GitHub mutations require production_guarded mode")
        self.manifest.validate()


class GuardedGitHubMutationTransport:
    """Fail-closed production transport with persisted idempotency and allowlists."""

    def __init__(
        self,
        store: JsonJobStore,
        client: GitHubMutationClient,
        config: ProductionMutationConfig,
    ):
        config.validate()
        self.store = store
        self.client = client
        self.config = config

    @staticmethod
    def _repository_name(command: MutationCommand) -> str:
        return f"{command.repository.owner}/{command.repository.name}"

    def _authorize(self, command: MutationCommand) -> None:
        repository = self._repository_name(command)
        if repository not in self.config.manifest.repository_allowlist:
            raise GitHubAdapterError(
                AdapterErrorKind.PERMISSION,
                f"Repository is not allowlisted for production mutations: {repository}",
            )
        if command.kind.value not in self.config.manifest.permitted_mutation_kinds:
            raise GitHubAdapterError(
                AdapterErrorKind.PERMISSION,
                f"Mutation kind is not permitted: {command.kind.value}",
            )
        if command.kind == MutationKind.SUBMIT_REVIEW and not self.config.reviews_enabled:
            raise GitHubAdapterError(AdapterErrorKind.PERMISSION, "Production reviews are disabled")
        if command.kind == MutationKind.MERGE_PULL_REQUEST and not self.config.merges_enabled:
            raise GitHubAdapterError(AdapterErrorKind.PERMISSION, "Production merges are disabled")

    def execute(self, command: MutationCommand) -> dict[str, Any]:
        self._authorize(command)
        existing = self.store.get_operation_result(command.operation_id)
        if existing is not None:
            return existing

        repository = self._repository_name(command)
        payload = command.payload
        try:
            if command.kind == MutationKind.CLAIM_ISSUE:
                result = self.client.claim_issue(repository, int(payload["issue_number"]))
            elif command.kind == MutationKind.CREATE_BRANCH:
                result = self.client.create_branch(repository, str(payload["branch"]), str(payload["base"]))
            elif command.kind == MutationKind.OPEN_PULL_REQUEST:
                result = self.client.open_pull_request(
                    repository,
                    title=str(payload.get("title") or f"Autonomy work for issue #{payload['issue_number']}"),
                    body=str(payload.get("body") or ""),
                    head=str(payload["head"]),
                    base=str(payload["base"]),
                )
            elif command.kind == MutationKind.SUBMIT_REVIEW:
                reviewed_head_sha = str(payload.get("reviewed_head_sha") or "")
                if not reviewed_head_sha:
                    raise GitHubAdapterError(AdapterErrorKind.CONFLICT, "Review requires reviewed_head_sha")
                result = self.client.submit_review(
                    repository,
                    pull_request_number=int(payload["pull_request_number"]),
                    event=str(payload["event"]),
                    reviewed_head_sha=reviewed_head_sha,
                )
            elif command.kind == MutationKind.MERGE_PULL_REQUEST:
                expected_head_sha = str(payload.get("expected_head_sha") or "")
                if not expected_head_sha:
                    raise GitHubAdapterError(AdapterErrorKind.CONFLICT, "Merge requires expected_head_sha")
                result = self.client.merge_pull_request(
                    repository,
                    pull_request_number=int(payload["pull_request_number"]),
                    merge_method=str(payload.get("merge_method") or "squash"),
                    expected_head_sha=expected_head_sha,
                )
            else:
                raise GitHubAdapterError(AdapterErrorKind.INVALID_RESPONSE, f"Unsupported mutation: {command.kind}")
        except GitHubAdapterError:
            raise
        except PermissionError as exc:
            raise GitHubAdapterError(AdapterErrorKind.PERMISSION, str(exc)) from exc
        except FileNotFoundError as exc:
            raise GitHubAdapterError(AdapterErrorKind.NOT_FOUND, str(exc)) from exc
        except TimeoutError as exc:
            raise GitHubAdapterError(AdapterErrorKind.TRANSIENT, str(exc), retryable=True) from exc
        except RuntimeError as exc:
            raise GitHubAdapterError(AdapterErrorKind.CONFLICT, str(exc)) from exc

        persisted = {
            "operation_id": command.operation_id,
            "kind": command.kind.value,
            "repository": repository,
            "result": result,
        }
        from .contracts import AuditEvent, utc_now

        event = AuditEvent(
            event_id=f"production-github:{command.operation_id}",
            job_id=str(payload.get("job_id") or "external"),
            operation_id=command.operation_id,
            event_type="github.mutation.executed",
            timestamp=utc_now(),
            details={"command": asdict(command), "result": result},
        )
        self.store.record_operation_result(event.job_id, command.operation_id, persisted, event)
        return persisted


class ProductionMutationExecutor:
    def __init__(self, transport: GuardedGitHubMutationTransport):
        self.transport = transport

    def execute(self, command: MutationCommand) -> MutationResult:
        details = self.transport.execute(command)
        return MutationResult(
            operation_id=command.operation_id,
            kind=command.kind,
            executed=True,
            dry_run=False,
            details=details,
        )
