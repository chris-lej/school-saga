from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Protocol

from .contracts import AuditEvent, RepositoryTarget, utc_now


class AdapterErrorKind(str, Enum):
    NOT_FOUND = "not_found"
    PERMISSION = "permission"
    RATE_LIMIT = "rate_limit"
    CONFLICT = "conflict"
    TRANSIENT = "transient"
    INVALID_RESPONSE = "invalid_response"


class GitHubAdapterError(RuntimeError):
    def __init__(self, kind: AdapterErrorKind, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable


@dataclass(frozen=True)
class IssueSnapshot:
    number: int
    title: str
    body: str
    state: str
    labels: tuple[str, ...] = ()


@dataclass(frozen=True)
class PullRequestSnapshot:
    number: int
    state: str
    draft: bool
    head_branch: str
    head_sha: str
    base_branch: str


@dataclass(frozen=True)
class CheckSnapshot:
    sha: str
    state: str
    successful: bool


class MutationKind(str, Enum):
    CLAIM_ISSUE = "claim_issue"
    CREATE_BRANCH = "create_branch"
    OPEN_PULL_REQUEST = "open_pull_request"
    SUBMIT_REVIEW = "submit_review"
    MERGE_PULL_REQUEST = "merge_pull_request"


@dataclass(frozen=True)
class MutationCommand:
    operation_id: str
    kind: MutationKind
    repository: RepositoryTarget
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MutationResult:
    operation_id: str
    kind: MutationKind
    executed: bool
    dry_run: bool
    details: dict[str, Any] = field(default_factory=dict)


class GitHubReadTransport(Protocol):
    def get_repository(self, repository: RepositoryTarget) -> dict[str, Any]: ...

    def get_issue(self, repository: RepositoryTarget, issue_number: int) -> dict[str, Any]: ...

    def get_pull_request(self, repository: RepositoryTarget, pr_number: int) -> dict[str, Any]: ...

    def get_checks(self, repository: RepositoryTarget, sha: str) -> dict[str, Any]: ...


class MutationTransport(Protocol):
    def execute(self, command: MutationCommand) -> dict[str, Any]: ...


class GitHubAdapter:
    def __init__(self, read_transport: GitHubReadTransport):
        self.read_transport = read_transport

    def repository(self, target: RepositoryTarget) -> RepositoryTarget:
        data = self.read_transport.get_repository(target)
        try:
            owner = data["owner"]["login"]
            name = data["name"]
            default_branch = data["default_branch"]
        except (KeyError, TypeError) as exc:
            raise GitHubAdapterError(AdapterErrorKind.INVALID_RESPONSE, "Invalid repository response") from exc
        return RepositoryTarget(owner=owner, name=name, default_branch=default_branch)

    def issue(self, target: RepositoryTarget, issue_number: int) -> IssueSnapshot:
        data = self.read_transport.get_issue(target, issue_number)
        try:
            labels = tuple(label["name"] for label in data.get("labels", []))
            return IssueSnapshot(
                number=int(data["number"]),
                title=str(data["title"]),
                body=str(data.get("body") or ""),
                state=str(data["state"]),
                labels=labels,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise GitHubAdapterError(AdapterErrorKind.INVALID_RESPONSE, "Invalid issue response") from exc

    def pull_request(self, target: RepositoryTarget, pr_number: int) -> PullRequestSnapshot:
        data = self.read_transport.get_pull_request(target, pr_number)
        try:
            return PullRequestSnapshot(
                number=int(data["number"]),
                state=str(data["state"]),
                draft=bool(data["draft"]),
                head_branch=str(data["head"]["ref"]),
                head_sha=str(data["head"]["sha"]),
                base_branch=str(data["base"]["ref"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise GitHubAdapterError(AdapterErrorKind.INVALID_RESPONSE, "Invalid pull request response") from exc

    def checks(self, target: RepositoryTarget, sha: str) -> CheckSnapshot:
        data = self.read_transport.get_checks(target, sha)
        try:
            state = str(data["state"])
        except (KeyError, TypeError) as exc:
            raise GitHubAdapterError(AdapterErrorKind.INVALID_RESPONSE, "Invalid checks response") from exc
        return CheckSnapshot(sha=sha, state=state, successful=state == "success")


class DryRunMutationExecutor:
    def __init__(self):
        self._results: dict[str, MutationResult] = {}
        self._events: list[AuditEvent] = []

    def execute(self, job_id: str, command: MutationCommand) -> MutationResult:
        existing = self._results.get(command.operation_id)
        if existing is not None:
            return existing
        result = MutationResult(
            operation_id=command.operation_id,
            kind=command.kind,
            executed=False,
            dry_run=True,
            details={"repository": asdict(command.repository), "payload": command.payload},
        )
        self._results[command.operation_id] = result
        self._events.append(
            AuditEvent(
                event_id=f"{job_id}:github-dry-run:{command.operation_id}",
                job_id=job_id,
                operation_id=command.operation_id,
                event_type="github.mutation.dry_run",
                timestamp=utc_now(),
                details={"kind": command.kind.value, **result.details},
            )
        )
        return result

    def events(self) -> list[AuditEvent]:
        return list(self._events)


class GuardedMutationExecutor:
    def __init__(self, transport: MutationTransport | None = None, *, mutations_enabled: bool = False):
        if mutations_enabled and transport is None:
            raise ValueError("Mutation mode requires an explicit mutation transport")
        self.transport = transport
        self.mutations_enabled = mutations_enabled

    def execute(self, command: MutationCommand) -> MutationResult:
        if not self.mutations_enabled or self.transport is None:
            raise GitHubAdapterError(
                AdapterErrorKind.PERMISSION,
                "GitHub mutation mode is disabled; use DryRunMutationExecutor or explicitly enable a transport",
            )
        details = self.transport.execute(command)
        return MutationResult(
            operation_id=command.operation_id,
            kind=command.kind,
            executed=True,
            dry_run=False,
            details=details,
        )
