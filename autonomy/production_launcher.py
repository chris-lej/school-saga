from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Protocol

from .deployment import DeploymentCommand, ProductionDeploymentConfig
from .live_cli import ProductionComposition


class ConcreteReadinessVerifier(Protocol):
    def verify(self, config: ProductionDeploymentConfig) -> str: ...


class ConcreteLifecycleRuntime(Protocol):
    def run_cycle(self) -> dict: ...


@dataclass(frozen=True)
class LauncherEnvironment:
    token_variable: str
    signing_key_variable: str
    emergency_stop_variable: str

    def validate(self) -> None:
        missing = [
            name
            for name, variable in (
                ("token", self.token_variable),
                ("signing_key", self.signing_key_variable),
                ("emergency_stop", self.emergency_stop_variable),
            )
            if not variable or variable not in os.environ
        ]
        if missing:
            raise RuntimeError(f"Missing launcher environment: {', '.join(missing)}")


@dataclass
class ProductionLauncher:
    composition: ProductionComposition
    environment: LauncherEnvironment

    @classmethod
    def build(
        cls,
        config_path: str | Path,
        *,
        readiness: ConcreteReadinessVerifier,
        runtime: ConcreteLifecycleRuntime,
    ) -> "ProductionLauncher":
        config = ProductionDeploymentConfig.from_json(config_path)
        environment = LauncherEnvironment(
            token_variable=config.token_source,
            signing_key_variable=config.signing_key_source,
            emergency_stop_variable=config.emergency_stop_source,
        )
        environment.validate()
        composition = ProductionComposition.build(
            config_path,
            readiness=readiness,
            runtime=runtime,
        )
        return cls(composition, environment)

    def execute(self, command: DeploymentCommand) -> dict:
        result = self.composition.execute(command)
        return {
            "command": command.value,
            "repository": self.composition.config.repository,
            "mode": self.composition.config.mode.value,
            "result": result,
        }


def run_launcher(
    config_path: str | Path,
    command: str,
    *,
    readiness: ConcreteReadinessVerifier,
    runtime: ConcreteLifecycleRuntime,
) -> str:
    launcher = ProductionLauncher.build(config_path, readiness=readiness, runtime=runtime)
    payload = launcher.execute(DeploymentCommand(command))
    return json.dumps(payload, sort_keys=True)


def redacted_config(config: ProductionDeploymentConfig) -> dict:
    payload = asdict(config)
    for key in ("token_source", "signing_key_source"):
        if payload.get(key):
            payload[key] = "<redacted>"
    return payload
