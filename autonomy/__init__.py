"""Autonomous engineering platform v2 foundation."""

from .contracts import Job, JobState, RepositoryTarget
from .github_adapter import (
    DryRunMutationExecutor,
    GitHubAdapter,
    GitHubAdapterError,
    GuardedMutationExecutor,
    MutationCommand,
    MutationKind,
)
from .store import JsonJobStore
from .validation import (
    SubprocessCommandRunner,
    ValidationCommand,
    ValidationRunResult,
    ValidationService,
    ValidationStatus,
    ValidationStepResult,
)

__all__ = [
    "DryRunMutationExecutor",
    "GitHubAdapter",
    "GitHubAdapterError",
    "GuardedMutationExecutor",
    "Job",
    "JobState",
    "JsonJobStore",
    "MutationCommand",
    "MutationKind",
    "RepositoryTarget",
    "SubprocessCommandRunner",
    "ValidationCommand",
    "ValidationRunResult",
    "ValidationService",
    "ValidationStatus",
    "ValidationStepResult",
]
