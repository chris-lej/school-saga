from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from autonomy.deployment import DeploymentCommand
from autonomy.live_cli import (
    EnvironmentEmergencyStop,
    FileLeaseStore,
    ProductionComposition,
    _redact,
)


@dataclass
class ReadinessFixture:
    reference: str = "ready-report"
    calls: int = 0

    def verify(self, config) -> str:
        self.calls += 1
        return self.reference


@dataclass
class RuntimeFixture:
    results: list[dict] = field(default_factory=lambda: [{"status": "completed", "issue_number": 82}])
    calls: int = 0

    def run_cycle(self) -> dict:
        self.calls += 1
        return self.results.pop(0)


class LiveCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state_path = self.root / "deployment-state.json"
        self.config_path = self.root / "deployment.json"
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

    def tearDown(self):
        self.temp.cleanup()

    def test_readiness_command_uses_real_configuration_loader(self):
        readiness = ReadinessFixture()
        composition = ProductionComposition.build(self.config_path, readiness=readiness, runtime=RuntimeFixture())
        result = composition.execute(DeploymentCommand.READINESS)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(readiness.calls, 1)

    def test_observe_mode_persists_scheduler_state(self):
        composition = ProductionComposition.build(
            self.config_path,
            readiness=ReadinessFixture(),
            runtime=RuntimeFixture(),
        )
        result = composition.execute(DeploymentCommand.OBSERVE)
        self.assertIn(result["status"], {"idle", "halted", "failed"})
        self.assertTrue(self.state_path.exists())

    def test_single_cycle_executes_one_runtime_cycle(self):
        runtime = RuntimeFixture()
        composition = ProductionComposition.build(self.config_path, readiness=ReadinessFixture(), runtime=runtime)
        result = composition.execute(DeploymentCommand.SINGLE_CYCLE)
        self.assertEqual(runtime.calls, 1)
        self.assertEqual(result["state"]["cycle_count"], 1)

    def test_file_lease_blocks_live_competitor_and_recovers_stale_lease(self):
        lease_path = self.root / "scheduler.lease.json"
        first = FileLeaseStore(lease_path, ttl_seconds=10)
        second = FileLeaseStore(lease_path, ttl_seconds=10)
        self.assertTrue(first.acquire("owner-a"))
        self.assertFalse(second.acquire("owner-b"))
        stale = {
            "owner": "owner-a",
            "heartbeat_at": (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat(),
        }
        lease_path.write_text(json.dumps(stale), encoding="utf-8")
        self.assertTrue(second.acquire("owner-b"))

    def test_emergency_stop_reads_environment(self):
        import os

        os.environ["AUTONOMY_TEST_STOP"] = "true"
        try:
            self.assertTrue(EnvironmentEmergencyStop("AUTONOMY_TEST_STOP").active())
        finally:
            os.environ.pop("AUTONOMY_TEST_STOP", None)

    def test_redaction_removes_secret_values(self):
        result = _redact({"token": "abc", "nested": {"signing_key_source": "env", "value": 1}})
        self.assertEqual(result["token"], "<redacted>")
        self.assertEqual(result["nested"]["signing_key_source"], "<redacted>")
        self.assertEqual(result["nested"]["value"], 1)


if __name__ == "__main__":
    unittest.main()
