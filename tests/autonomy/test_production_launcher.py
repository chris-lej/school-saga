from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import tempfile
import unittest

from autonomy.deployment import DeploymentCommand
from autonomy.production_launcher import ProductionLauncher, redacted_config


@dataclass
class ReadinessFixture:
    reference: str = "ready-report"
    calls: int = 0

    def verify(self, config) -> str:
        self.calls += 1
        return self.reference


@dataclass
class RuntimeFixture:
    results: list[dict] = field(default_factory=lambda: [{"status": "completed", "issue_number": 84}])
    calls: int = 0

    def run_cycle(self) -> dict:
        self.calls += 1
        return self.results.pop(0)


class ProductionLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config_path = self.root / "deployment.json"
        self.state_path = self.root / "state.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "repository": "chris-lej/school-saga",
                    "repository_root": str(self.root),
                    "expected_main_sha": "main-sha",
                    "path_allowlist": ["autonomy", "tests/autonomy", "docs"],
                    "command_allowlist": ["bash scripts/validate-pr.sh"],
                    "mutation_allowlist": ["claim_issue", "create_branch", "open_pull_request", "review", "merge"],
                    "required_checks": ["Godot Validation"],
                    "token_source": "GITHUB_TOKEN",
                    "signing_key_source": "AUTONOMY_SIGNING_KEY",
                    "emergency_stop_source": "AUTONOMY_STOP",
                    "audit_store": str(self.root / "audit.json"),
                    "lease_owner": "scheduler-1",
                    "state_path": str(self.state_path),
                    "mode": "observe_only",
                    "max_cycles_per_run": 1,
                    "retry_backoff_seconds": 5,
                    "enabled": True,
                }
            ),
            encoding="utf-8",
        )
        self.saved = {name: os.environ.get(name) for name in ("GITHUB_TOKEN", "AUTONOMY_SIGNING_KEY", "AUTONOMY_STOP")}
        os.environ["GITHUB_TOKEN"] = "fixture-token"
        os.environ["AUTONOMY_SIGNING_KEY"] = "fixture-key"
        os.environ["AUTONOMY_STOP"] = "false"

    def tearDown(self):
        for name, value in self.saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.temp.cleanup()

    def test_readiness_uses_concrete_adapters(self):
        readiness = ReadinessFixture()
        launcher = ProductionLauncher.build(self.config_path, readiness=readiness, runtime=RuntimeFixture())
        result = launcher.execute(DeploymentCommand.READINESS)
        self.assertEqual(result["result"]["status"], "ready")
        self.assertEqual(readiness.calls, 1)

    def test_single_cycle_runs_runtime(self):
        runtime = RuntimeFixture()
        launcher = ProductionLauncher.build(self.config_path, readiness=ReadinessFixture(), runtime=runtime)
        result = launcher.execute(DeploymentCommand.SINGLE_CYCLE)
        self.assertEqual(runtime.calls, 1)
        self.assertIn(result["result"]["status"], {"idle", "halted", "failed"})

    def test_missing_secret_environment_fails_closed(self):
        os.environ.pop("GITHUB_TOKEN", None)
        with self.assertRaises(RuntimeError):
            ProductionLauncher.build(self.config_path, readiness=ReadinessFixture(), runtime=RuntimeFixture())

    def test_config_redaction_hides_secret_sources(self):
        launcher = ProductionLauncher.build(self.config_path, readiness=ReadinessFixture(), runtime=RuntimeFixture())
        payload = redacted_config(launcher.composition.config)
        self.assertEqual(payload["token_source"], "<redacted>")
        self.assertEqual(payload["signing_key_source"], "<redacted>")


if __name__ == "__main__":
    unittest.main()
