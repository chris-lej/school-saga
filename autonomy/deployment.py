from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from pathlib import Path
from typing import Protocol

from .unattended_scheduler import (
    BoundedUnattendedScheduler,
    DeploymentMode,
    SchedulerControl,
    SchedulerHealth,
    UnattendedSchedulerConfig,
)


class DeploymentCommand(str, Enum):
    READINESS = "readiness"
    OBSERVE = "observe"
    SINGLE_CYCLE = "single_cycle"
    ALWAYS_ON = "always_on"
    PAUSE = "pause"
    RESUME = "resume"
    DRAIN = "drain"
    STATUS = "status"
    SHUTDOWN = "shutdown"


@dataclass(frozen=True)
class ProductionDeploymentConfig:
    repository: str
    repository_root: str
    expected_main_sha: str
    path_allowlist: tuple[str, ...]
    command_allowlist: tuple[str, ...]
    mutation_allowlist: tuple[str, ...]
    required_checks: tuple[str, ...]
    token_source: str
    signing_key_source: str
    emergency_stop_source: str
    audit_store: str
    lease_owner: str
    state_path: str
    mode: DeploymentMode = DeploymentMode.OBSERVE_ONLY
    max_cycles_per_run: int = 1
    retry_backoff_seconds: int = 60
    enabled: bool = False

    def validate(self) -> None:
        if not self.enabled:
            raise ValueError("Production deployment is disabled")
        required = {
            "repository": self.repository,
            "repository_root": self.repository_root,
            "expected_main_sha": self.expected_main_sha,
            "token_source": self.token_source,
            "signing_key_source": self.signing_key_source,
            "emergency_stop_source": self.emergency_stop_source,
            "audit_store": self.audit_store,
            "lease_owner": self.lease_owner,
            "state_path": self.state_path,
        }
        missing = tuple(name for name, value in required.items() if not value)
        if missing:
            raise ValueError(f"Missing deployment configuration: {', '.join(missing)}")
        if not all((self.path_allowlist, self.command_allowlist, self.mutation_allowlist, self.required_checks)):
            raise ValueError("All deployment allowlists and required checks must be non-empty")
        if self.max_cycles_per_run < 1:
            raise ValueError("max_cycles_per_run must be at least one")
        if self.retry_backoff_seconds < 1:
            raise ValueError("retry_backoff_seconds must be positive")

    @classmethod
    def from_json(cls, path: str | Path) -> "ProductionDeploymentConfig":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        payload["mode"] = DeploymentMode(payload.get("mode", DeploymentMode.OBSERVE_ONLY.value))
        for key in ("path_allowlist", "command_allowlist", "mutation_allowlist", "required_checks"):
            payload[key] = tuple(payload.get(key, ()))
        config = cls(**payload)
        config.validate()
        return config


@dataclass(frozen=True)
class PersistedDeploymentState:
    readiness_reference: str = ""
    scheduler_state: str = "idle"
    active_issue: int | None = None
    last_successful_cycle: int | None = None
    failed_cycles: int = 0
    quarantined_issues: tuple[int, ...] = field(default_factory=tuple)
    cycle_count: int = 0


class DeploymentStateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> PersistedDeploymentState:
        if not self.path.exists():
            return PersistedDeploymentState()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload["quarantined_issues"] = tuple(payload.get("quarantined_issues", ()))
        return PersistedDeploymentState(**payload)

    def save_health(self, health: SchedulerHealth) -> PersistedDeploymentState:
        prior = self.load()
        state = PersistedDeploymentState(
            readiness_reference=health.readiness_reference,
            scheduler_state=health.state.value,
            active_issue=health.active_issue,
            last_successful_cycle=health.last_successful_cycle,
            failed_cycles=health.failed_cycles,
            quarantined_issues=health.quarantined_issues,
            cycle_count=prior.cycle_count + len(health.cycles),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(asdict(state), sort_keys=True, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)
        return state


class StartupProbe(Protocol):
    def verify(self, config: ProductionDeploymentConfig) -> str: ...


class SchedulerFactory(Protocol):
    def build(
        self,
        config: ProductionDeploymentConfig,
        control: SchedulerControl,
    ) -> BoundedUnattendedScheduler: ...


@dataclass
class ProductionDeploymentRuntime:
    probe: StartupProbe
    scheduler_factory: SchedulerFactory
    control: SchedulerControl
    state_store: DeploymentStateStore

    def execute(self, command: DeploymentCommand, config: ProductionDeploymentConfig) -> dict:
        config.validate()
        if command == DeploymentCommand.PAUSE:
            self.control.pause()
            return {"status": "paused"}
        if command == DeploymentCommand.RESUME:
            self.control.resume()
            return {"status": "resumed"}
        if command == DeploymentCommand.DRAIN:
            self.control.drain()
            return {"status": "draining"}
        if command == DeploymentCommand.SHUTDOWN:
            self.control.shutdown()
            return {"status": "shutdown_requested"}
        if command == DeploymentCommand.STATUS:
            return asdict(self.state_store.load())

        readiness_reference = self.probe.verify(config)
        if command == DeploymentCommand.READINESS:
            return {"status": "ready", "readiness_reference": readiness_reference}

        mode = {
            DeploymentCommand.OBSERVE: DeploymentMode.OBSERVE_ONLY,
            DeploymentCommand.SINGLE_CYCLE: DeploymentMode.SINGLE_CYCLE,
            DeploymentCommand.ALWAYS_ON: DeploymentMode.ALWAYS_ON,
        }[command]
        runtime_config = ProductionDeploymentConfig(**{**config.__dict__, "mode": mode})
        scheduler = self.scheduler_factory.build(runtime_config, self.control)
        health = scheduler.run()
        persisted = self.state_store.save_health(health)
        return {"status": health.state.value, "state": asdict(persisted)}


def scheduler_config(config: ProductionDeploymentConfig) -> UnattendedSchedulerConfig:
    return UnattendedSchedulerConfig(
        mode=config.mode,
        max_cycles_per_run=config.max_cycles_per_run,
        one_active_issue=True,
        lease_owner=config.lease_owner,
        retry_backoff_seconds=config.retry_backoff_seconds,
    )
