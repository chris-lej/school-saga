from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobState(str, Enum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    EXECUTING = "executing"
    VALIDATING = "validating"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    MERGING = "merging"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATES = {
    JobState.COMPLETED,
    JobState.BLOCKED,
    JobState.FAILED,
    JobState.CANCELLED,
}

ALLOWED_TRANSITIONS: dict[JobState, set[JobState]] = {
    JobState.QUEUED: {JobState.CLAIMED, JobState.CANCELLED},
    JobState.CLAIMED: {JobState.EXECUTING, JobState.BLOCKED, JobState.FAILED, JobState.CANCELLED},
    JobState.EXECUTING: {JobState.VALIDATING, JobState.BLOCKED, JobState.FAILED, JobState.CANCELLED},
    JobState.VALIDATING: {JobState.REVIEWING, JobState.EXECUTING, JobState.BLOCKED, JobState.FAILED, JobState.CANCELLED},
    JobState.REVIEWING: {JobState.APPROVED, JobState.EXECUTING, JobState.BLOCKED, JobState.FAILED, JobState.CANCELLED},
    JobState.APPROVED: {JobState.MERGING, JobState.BLOCKED, JobState.FAILED, JobState.CANCELLED},
    JobState.MERGING: {JobState.COMPLETED, JobState.BLOCKED, JobState.FAILED, JobState.CANCELLED},
    JobState.COMPLETED: set(),
    JobState.BLOCKED: set(),
    JobState.FAILED: set(),
    JobState.CANCELLED: set(),
}


@dataclass(frozen=True)
class RepositoryTarget:
    owner: str
    name: str
    default_branch: str = "main"
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True)
class IssueWorkRequest:
    issue_number: int
    title: str
    body: str = ""
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True)
class WorkerResult:
    branch: str
    commit_sha: str | None = None
    pull_request_number: int | None = None
    summary: str = ""
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    command: str
    summary: str = ""
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True)
class ReviewResult:
    approved: bool
    summary: str = ""
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True)
class MergeDecision:
    allowed: bool
    reason: str
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    job_id: str
    operation_id: str
    event_type: str
    timestamp: str
    from_state: str | None = None
    to_state: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION


@dataclass
class Job:
    repository: RepositoryTarget
    request: IssueWorkRequest
    job_id: str = field(default_factory=lambda: str(uuid4()))
    state: JobState = JobState.QUEUED
    attempts: int = 0
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported job schema version: {data.get('schema_version')!r}; expected {SCHEMA_VERSION}"
            )
        return cls(
            repository=RepositoryTarget(**data["repository"]),
            request=IssueWorkRequest(**data["request"]),
            job_id=data["job_id"],
            state=JobState(data["state"]),
            attempts=int(data["attempts"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            schema_version=data["schema_version"],
        )

    def transition(self, target: JobState) -> tuple[JobState, JobState]:
        allowed = ALLOWED_TRANSITIONS[self.state]
        if target not in allowed:
            allowed_values = ", ".join(sorted(state.value for state in allowed)) or "none"
            raise ValueError(
                f"Invalid job transition {self.state.value!r} -> {target.value!r}; allowed targets: {allowed_values}"
            )
        previous = self.state
        self.state = target
        self.updated_at = utc_now()
        if target == JobState.EXECUTING:
            self.attempts += 1
        return previous, target
