from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tempfile
import unittest

from autonomy.deployment import (
    DeploymentCommand,
    DeploymentStateStore,
    ProductionDeploymentConfig,
    ProductionDeploymentRuntime,
)
from autonomy.unattended_scheduler import (
    BoundedUnattendedScheduler,
    DeploymentMode,
    SchedulerControl,
    UnattendedSchedulerConfig,
)


@dataclass
class ProbeFixture:
    reference: str = "ready-report"
    calls: int = 0

    def verify(self, config: ProductionDeploymentConfig) -> str:
        self.calls += 1
        return self.reference


@dataclass
class ReadinessFixture:
    reference: str = "ready-report"

    def verify(self) -> str:
        return self.reference


@dataclass
class StopFixture:
    active_value: bool = False

    def active(self) -> bool:
        return self.active_value


@dataclass
class LeaseFixture:
    available: bool = True

    def acquire(self, owner: str) -> bool:
        return self.available

    def release(self, owner: str) -> None:
        return None

    def heartbeat(self, owner: str) -> None:
        return None


@dataclass
class RuntimeFixture:
    results: list[dict] = field(default_factory=lambda: [{"status": "completed", "issue_number": 80}])

    def run_cycle(self) -> dict:
        return self.results.pop(0)


@dataclass
class SchedulerFactoryFixture:
    runtime: RuntimeFixture = field(default_factory=RuntimeFixture)
    built_modes: list[DeploymentMode] = field(default_factory=list)

    def build(self, config: ProductionDeploymentConfig, control: SchedulerControl) -> BoundedUnattendedScheduler:
        self.built_modes.append(config.mode)
        return BoundedUnattendedScheduler(
            ReadinessFixture(),
            StopFixture(),
            LeaseFixture(),
            self.runtime,
            control,
            UnattendedSchedulerConfig(
                mode=config.mode,
                max_cycles_per_run=config.max_cycles_per_run,
                lease_owner=config.lease_owner,
                retry_backoff_seconds=config.retry_backoff_seconds,
            ),
        )


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = ProductionDeploymentConfig(
            repository="chris-lej/school-saga",
            repository_root=str(self.root),
            expected_main_sha="main-sha",
            path_allowlist=("autonomy", "tests/autonomy", "docs"),
            command_allowlist=("bash scripts/validate-pr.sh",),
            mutation_allowlist=("claim_issue", "create_branch", "open_pull_request", "review", "merge"),
            required_checks=("Godot Validation",),
            token_source="environment",
            signing_key_source="environment",
            emergency_stop_source="environment",
            audit_store=str(self.root / "audit.json"),
            lease_owner="scheduler-1",
            state_path=str(self.root / "deployment-state.json"),
            enabled=True,
        )
        self.probe = ProbeFixture()
        self.factory = SchedulerFactoryFixture()
        self.control = SchedulerControl()
        self.store = DeploymentStateStore(self.config.state_path)
        self.runtime = ProductionDeploymentRuntime(self.probe, self.factory, self.control, self.store)

    def tearDown(self):
        self.temp.cleanup()

    def test_readiness_command_performs_no_scheduler_cycle(self):
        result = self.runtime.execute(DeploymentCommand.READINESS, self.config)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(self.factory.built_modes, [])

    def test_observe_mode_is_default_safe_launch(self):
        result = self.runtime.execute(DeploymentCommand.OBSERVE, self.config)
        self.assertEqual(self.factory.built_modes, [DeploymentMode.OBSERVE_ONLY])
        self.assertEqual(result["status"], "idle")

    def test_single_cycle_persists_scheduler_state(self):
        result = self.runtime.execute(DeploymentCommand.SINGLE_CYCLE, self.config)
        self.assertEqual(self.factory.built_modes, [DeploymentMode.SINGLE_CYCLE])
        self.assertEqual(result["state"]["last_successful_cycle"], 1)
        self.assertEqual(self.runtime.execute(DeploymentCommand.STATUS, self.config)["cycle_count"], 1)

    def test_control_commands_mutate_shared_control_state(self):
        self.runtime.execute(DeploymentCommand.PAUSE, self.config)
        self.assertTrue(self.control.paused)
        self.runtime.execute(DeploymentCommand.RESUME, self.config)
        self.assertFalse(self.control.paused)
        self.runtime.execute(DeploymentCommand.DRAIN, self.config)
        self.assertTrue(self.control.draining)
        self.runtime.execute(DeploymentCommand.SHUTDOWN, self.config)
        self.assertTrue(self.control.shutdown_requested)

    def test_disabled_configuration_fails_closed(self):
        disabled = ProductionDeploymentConfig(**{**self.config.__dict__, "enabled": False})
        with self.assertRaises(ValueError):
            self.runtime.execute(DeploymentCommand.OBSERVE, disabled)


if __name__ == "__main__":
    unittest.main()
