from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from autonomy.readiness import (
    ProductionReadinessGate,
    ReadinessConfig,
    ReadinessError,
    ReadinessGate,
    ReadinessStatus,
    SignedReadinessReport,
    StaticReadinessProbe,
)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 25, 13, 0, tzinfo=timezone.utc)
        self.config = ReadinessConfig(
            repository="chris-lej/school-saga",
            repository_sha="abc123",
            operator="chris-lej",
            report_ttl_seconds=3600,
            path_allowlist=("autonomy", "tests/autonomy", "docs"),
            command_allowlist=("python -m unittest discover -s tests/autonomy -p 'test_*.py'", "bash scripts/validate-pr.sh"),
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
                ReadinessGate("branch_protection_visible", True),
                ReadinessGate("required_checks_available", True),
                ReadinessGate("emergency_stop_reachable", True),
                ReadinessGate("audit_store_writable", True),
                ReadinessGate("restart_recovery_verified", True),
            )),
            b"fixture-signing-key",
        )

    def test_complete_configuration_produces_ready_report(self):
        report = self.gate.evaluate(self.config, now=self.now)
        self.assertEqual(report.status, ReadinessStatus.READY)
        self.assertTrue(report.signature)
        self.gate.verify(report, self.config, now=self.now + timedelta(minutes=1))

    def test_failed_probe_produces_not_ready_report(self):
        gate = ProductionReadinessGate(
            StaticReadinessProbe((ReadinessGate("required_checks_available", False, "missing"),)),
            b"fixture-signing-key",
        )
        report = gate.evaluate(self.config, now=self.now)
        self.assertEqual(report.status, ReadinessStatus.NOT_READY)
        self.assertIn("required_checks_available", report.unresolved_risks)
        with self.assertRaises(ReadinessError):
            gate.verify(report, self.config, now=self.now)

    def test_moved_main_invalidates_report(self):
        report = self.gate.evaluate(self.config, now=self.now)
        moved = replace(self.config, repository_sha="def456")
        with self.assertRaises(ReadinessError):
            self.gate.verify(report, moved, now=self.now)

    def test_configuration_change_invalidates_report(self):
        report = self.gate.evaluate(self.config, now=self.now)
        changed = replace(self.config, max_fix_iterations=4)
        with self.assertRaises(ReadinessError):
            self.gate.verify(report, changed, now=self.now)

    def test_expired_report_is_rejected(self):
        report = self.gate.evaluate(self.config, now=self.now)
        with self.assertRaises(ReadinessError):
            self.gate.verify(report, self.config, now=self.now + timedelta(hours=2))

    def test_tampered_signature_is_rejected(self):
        report = self.gate.evaluate(self.config, now=self.now)
        tampered = SignedReadinessReport(**{**report.__dict__, "signature": "bad"})
        with self.assertRaises(ReadinessError):
            self.gate.verify(tampered, self.config, now=self.now)

    def test_high_risk_capability_fails_closed(self):
        unsafe = replace(self.config, unattended_scheduler_enabled=True)
        report = self.gate.evaluate(unsafe, now=self.now)
        self.assertEqual(report.status, ReadinessStatus.NOT_READY)
        self.assertIn("unattended_scheduler_disabled", report.unresolved_risks)


if __name__ == "__main__":
    unittest.main()
