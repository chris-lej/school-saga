from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import argparse
import json
import os
from pathlib import Path
from typing import Protocol

from .deployment import (
    DeploymentCommand,
    DeploymentStateStore,
    ProductionDeploymentConfig,
    ProductionDeploymentRuntime,
)
from .unattended_scheduler import (
    BoundedUnattendedScheduler,
    SchedulerControl,
)


@dataclass(frozen=True)
class EnvironmentEmergencyStop:
    variable: str

    def active(self) -> bool:
        return os.environ.get(self.variable, "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class FileLeaseRecord:
    owner: str
    heartbeat_at: str


class FileLeaseStore:
    def __init__(self, path: str | Path, *, ttl_seconds: int = 300):
        self.path = Path(path)
        self.ttl_seconds = ttl_seconds

    def _load(self) -> FileLeaseRecord | None:
        if not self.path.exists():
            return None
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return FileLeaseRecord(**payload)

    def acquire(self, owner: str) -> bool:
        now = datetime.now(timezone.utc)
        existing = self._load()
        if existing is not None:
            heartbeat = datetime.fromisoformat(existing.heartbeat_at)
            if existing.owner != owner and now - heartbeat < timedelta(seconds=self.ttl_seconds):
                return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write(FileLeaseRecord(owner, now.isoformat()))
        return True

    def heartbeat(self, owner: str) -> None:
        existing = self._load()
        if existing is None or existing.owner != owner:
            raise RuntimeError("Scheduler lease is not owned by this process")
        self._write(FileLeaseRecord(owner, datetime.now(timezone.utc).isoformat()))

    def release(self, owner: str) -> None:
        existing = self._load()
        if existing is not None and existing.owner == owner:
            self.path.unlink(missing_ok=True)

    def _write(self, record: FileLeaseRecord) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(asdict(record), sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.path)


class RuntimeCycle(Protocol):
    def run_cycle(self) -> dict: ...


class ReadinessAdapter(Protocol):
    def verify(self, config: ProductionDeploymentConfig) -> str: ...


@dataclass
class ConcreteSchedulerFactory:
    readiness: ReadinessAdapter
    emergency_stop: EnvironmentEmergencyStop
    leases: FileLeaseStore
    runtime: RuntimeCycle

    def build(self, config: ProductionDeploymentConfig, control: SchedulerControl) -> BoundedUnattendedScheduler:
        from .deployment import scheduler_config

        class ConfigReadiness:
            def verify(inner_self) -> str:
                return self.readiness.verify(config)

        return BoundedUnattendedScheduler(
            ConfigReadiness(),
            self.emergency_stop,
            self.leases,
            self.runtime,
            control,
            scheduler_config(config),
        )


@dataclass
class ProductionComposition:
    deployment: ProductionDeploymentRuntime
    config: ProductionDeploymentConfig

    @classmethod
    def build(
        cls,
        config_path: str | Path,
        *,
        readiness: ReadinessAdapter,
        runtime: RuntimeCycle,
    ) -> "ProductionComposition":
        config = ProductionDeploymentConfig.from_json(config_path)
        emergency_stop = EnvironmentEmergencyStop(config.emergency_stop_source)
        lease_path = Path(config.state_path).with_suffix(".lease.json")
        factory = ConcreteSchedulerFactory(readiness, emergency_stop, FileLeaseStore(lease_path), runtime)
        deployment = ProductionDeploymentRuntime(
            readiness,
            factory,
            SchedulerControl(),
            DeploymentStateStore(config.state_path),
        )
        return cls(deployment, config)

    def execute(self, command: DeploymentCommand) -> dict:
        result = self.deployment.execute(command, self.config)
        return _redact(result)


def _redact(value):
    if isinstance(value, dict):
        return {
            key: ("<redacted>" if any(marker in key.lower() for marker in ("token", "secret", "signing_key")) else _redact(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="school-saga-autonomy")
    parser.add_argument("command", choices=[command.value for command in DeploymentCommand])
    parser.add_argument("--config", required=True)
    return parser


def main(argv: list[str] | None = None, *, readiness: ReadinessAdapter | None = None, runtime: RuntimeCycle | None = None) -> int:
    args = build_parser().parse_args(argv)
    if readiness is None or runtime is None:
        raise RuntimeError("Concrete readiness and production runtime adapters must be supplied by the deployment launcher")
    composition = ProductionComposition.build(args.config, readiness=readiness, runtime=runtime)
    result = composition.execute(DeploymentCommand(args.command))
    print(json.dumps(result, sort_keys=True))
    return 0
