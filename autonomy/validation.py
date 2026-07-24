from __future__ import annotations

import os
import subprocess
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol

from .contracts import AuditEvent, utc_now
from .store import JsonJobStore


class ValidationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    UNAVAILABLE = "unavailable"
    INFRASTRUCTURE_ERROR = "infrastructure_error"


@dataclass(frozen=True)
class ValidationCommand:
    name: str
    argv: tuple[str, ...]
    timeout_seconds: int = 300


@dataclass(frozen=True)
class ValidationStepResult:
    name: str
    status: ValidationStatus
    return_code: int | None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0

    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.PASSED


@dataclass(frozen=True)
class ValidationRunResult:
    operation_id: str
    attempt: int
    status: ValidationStatus
    steps: tuple[ValidationStepResult, ...] = field(default_factory=tuple)
    started_at: str = field(default_factory=utc_now)
    completed_at: str = field(default_factory=utc_now)

    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.PASSED


class CommandRunner(Protocol):
    def run(
        self,
        command: ValidationCommand,
        *,
        cwd: Path,
        environment: dict[str, str],
        max_output_chars: int,
    ) -> ValidationStepResult: ...


class SubprocessCommandRunner:
    def run(
        self,
        command: ValidationCommand,
        *,
        cwd: Path,
        environment: dict[str, str],
        max_output_chars: int,
    ) -> ValidationStepResult:
        import time

        started = time.monotonic()
        try:
            completed = subprocess.run(
                list(command.argv),
                cwd=cwd,
                env=environment,
                capture_output=True,
                text=True,
                timeout=command.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            return ValidationStepResult(
                name=command.name,
                status=ValidationStatus.UNAVAILABLE,
                return_code=None,
                stderr=str(exc)[:max_output_chars],
                duration_seconds=time.monotonic() - started,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
            return ValidationStepResult(
                name=command.name,
                status=ValidationStatus.TIMED_OUT,
                return_code=None,
                stdout=stdout[:max_output_chars],
                stderr=stderr[:max_output_chars],
                duration_seconds=time.monotonic() - started,
            )
        except OSError as exc:
            return ValidationStepResult(
                name=command.name,
                status=ValidationStatus.INFRASTRUCTURE_ERROR,
                return_code=None,
                stderr=str(exc)[:max_output_chars],
                duration_seconds=time.monotonic() - started,
            )

        status = ValidationStatus.PASSED if completed.returncode == 0 else ValidationStatus.FAILED
        return ValidationStepResult(
            name=command.name,
            status=status,
            return_code=completed.returncode,
            stdout=completed.stdout[:max_output_chars],
            stderr=completed.stderr[:max_output_chars],
            duration_seconds=time.monotonic() - started,
        )


class ValidationService:
    def __init__(
        self,
        store: JsonJobStore,
        runner: CommandRunner,
        *,
        commands: tuple[ValidationCommand, ...],
        cwd: str | Path,
        allowed_environment_keys: tuple[str, ...] = ("PATH", "HOME", "TMPDIR"),
        max_output_chars: int = 20000,
    ):
        self.store = store
        self.runner = runner
        self.commands = commands
        self.cwd = Path(cwd)
        self.allowed_environment_keys = allowed_environment_keys
        self.max_output_chars = max_output_chars

    def _environment(self) -> dict[str, str]:
        return {
            key: os.environ[key]
            for key in self.allowed_environment_keys
            if key in os.environ
        }

    def validate(self, job_id: str, operation_id: str) -> ValidationRunResult:
        existing = self.store.get_operation_result(operation_id)
        if existing is not None:
            return self._from_dict(existing)

        prior_attempts = self.store.count_events(job_id, "validation.completed")
        started_at = utc_now()
        steps: list[ValidationStepResult] = []
        environment = self._environment()
        for command in self.commands:
            step = self.runner.run(
                command,
                cwd=self.cwd,
                environment=environment,
                max_output_chars=self.max_output_chars,
            )
            steps.append(step)
            if not step.passed:
                break

        aggregate_status = ValidationStatus.PASSED
        for step in steps:
            if not step.passed:
                aggregate_status = step.status
                break

        result = ValidationRunResult(
            operation_id=operation_id,
            attempt=prior_attempts + 1,
            status=aggregate_status,
            steps=tuple(steps),
            started_at=started_at,
            completed_at=utc_now(),
        )
        event = AuditEvent(
            event_id=f"{job_id}:validation:{operation_id}",
            job_id=job_id,
            operation_id=operation_id,
            event_type="validation.completed",
            timestamp=result.completed_at,
            details={
                "attempt": result.attempt,
                "status": result.status.value,
                "steps": [asdict(step) | {"status": step.status.value} for step in result.steps],
            },
        )
        self.store.record_operation_result(
            job_id,
            operation_id,
            self._to_dict(result),
            event,
        )
        return result

    @staticmethod
    def _to_dict(result: ValidationRunResult) -> dict:
        return {
            "operation_id": result.operation_id,
            "attempt": result.attempt,
            "status": result.status.value,
            "steps": [asdict(step) | {"status": step.status.value} for step in result.steps],
            "started_at": result.started_at,
            "completed_at": result.completed_at,
        }

    @staticmethod
    def _from_dict(data: dict) -> ValidationRunResult:
        return ValidationRunResult(
            operation_id=data["operation_id"],
            attempt=int(data["attempt"]),
            status=ValidationStatus(data["status"]),
            steps=tuple(
                ValidationStepResult(
                    name=step["name"],
                    status=ValidationStatus(step["status"]),
                    return_code=step.get("return_code"),
                    stdout=step.get("stdout", ""),
                    stderr=step.get("stderr", ""),
                    duration_seconds=float(step.get("duration_seconds", 0.0)),
                )
                for step in data.get("steps", [])
            ),
            started_at=data["started_at"],
            completed_at=data["completed_at"],
        )
