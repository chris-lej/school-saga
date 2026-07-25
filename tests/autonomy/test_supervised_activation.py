from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import unittest

from autonomy.readiness import (
    ProductionReadinessGate,
    ReadinessConfig,
    ReadinessGate,
    StaticReadinessProbe,
)
from autonomy.supervised_activation import (
    SupervisedActivationConfig,
    SupervisedActivationStatus,
    SupervisedProductionActivation,
)


@dataclass
class StopFixture:
    value: bool = False

    def active(self) -> bool:
        return self.value


@dataclass
class ActiveJobFixture:
    value: bool = False

    def has_active_job(self) -> bool:
        return self.value


@dataclass
class RuntimeFixture:
    calls: list[int] = field(default_factory=list)

    def run_selected_issue(self, issue_number: int) -> dict:
        self.calls.append(issue_number)
        return {
            "issue_number": issue_number,
            "branch": f"autonomy/issue-{issue_number}",
            "commit_sha": "abc123",
            "pull_request_number": issue_number + 100,
            "operation_ids": ("claim", "branch", "commit", "pr", "review", "merge"),
        }


class SupervisedActivationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.readiness_config = ReadinessConfig(
            repository="chris-lej/school-saga",
            repository_sha="main-sha",
            operator="operator",
            report_ttl_seconds=3600,
            path_allowlist=("autonomy", "tests/autonomy", "docs"),
            command_allowlist=("bash scripts/validate-pr.sh",),
            mutation_allowlist=("claim_issue", "create_branch", "open_pull_request", "review", "merge"),
            required_checks=("Godot Validation",),
            token_scopes=("contents:write", "issues:write", "pull_requests:write"),
            emergency_stop_source="environment",
            audit_store="json-job-store",
            max_fix_iterations=3,
            quarantine_enabled=True,
        )
        self.gate = ProductionReadinessGate(
            StaticReadinessProbe((
                ReadinessGate("clean_worktree", True),
                ReadinessGate("required_checks_available", True),
                ReadinessGate("emergency_stop_reachable", True),
                ReadinessGate("audit_store_writable", True),
            )),
            b"fixture-signing-key",
        )
        self.report = self.gate.evaluate(self.readiness_config, now=self.now)
        self.stop = StopFixture()
        self.active = ActiveJobFixture()
        self.runtime = RuntimeFixture()
        self.activation = SupervisedProductionActivation(self.gate, self.stop, self.active, self.runtime)

    def config(self, **changes) -> SupervisedActivationConfig:
        values = {
            "enabled": True,
            "live_execution_confirmed": False,
            "selected_issue": 76,
            "dry_run": True,
        }
        values.update(changes)
        return SupervisedActivationConfig(**values)

    def test_dry_run_verifies_readiness_without_runtime(self):
        result = self.activation.run(self.config(), self.report, self.readiness_config)
        self.assertEqual(result.status, SupervisedActivationStatus.PREFLIGHT_ONLY)
        self.assertEqual(self.runtime.calls, [])

    def test_live_run_requires_explicit_confirmation(self):
        with self.assertRaises(ValueError):
            self.activation.run(self.config(dry_run=False), self.report, self.readiness_config)

    def test_live_run_executes_one_selected_issue(self):
        result = self.activation.run(
            self.config(dry_run=False, live_execution_confirmed=True),
            self.report,
            self.readiness_config,
        )
        self.assertEqual(result.status, SupervisedActivationStatus.COMPLETED)
        self.assertEqual(self.runtime.calls, [76])
        self.assertEqual(result.result["pull_request_number"], 176)

    def test_emergency_stop_halts_before_readiness_or_runtime(self):
        self.stop.value = True
        result = self.activation.run(self.config(), self.report, self.readiness_config)
        self.assertEqual(result.status, SupervisedActivationStatus.HALTED)
        self.assertEqual(self.runtime.calls, [])

    def test_active_job_blocks_live_execution(self):
        self.active.value = True
        result = self.activation.run(
            self.config(dry_run=False, live_execution_confirmed=True),
            self.report,
            self.readiness_config,
        )
        self.assertEqual(result.status, SupervisedActivationStatus.BLOCKED)
        self.assertEqual(self.runtime.calls, [])

    def test_moved_repository_sha_invalidates_readiness(self):
        moved = ReadinessConfig(**{**self.readiness_config.__dict__, "repository_sha": "moved"})
        with self.assertRaises(Exception):
            self.activation.run(self.config(), self.report, moved)


if __name__ == "__main__":
    unittest.main()
