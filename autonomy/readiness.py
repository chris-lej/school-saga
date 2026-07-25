from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import hmac
import json
from typing import Protocol


class ReadinessStatus(str, Enum):
    READY = "ready"
    NOT_READY = "not_ready"


@dataclass(frozen=True)
class ReadinessGate:
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class ReadinessConfig:
    repository: str
    repository_sha: str
    operator: str
    report_ttl_seconds: int
    path_allowlist: tuple[str, ...]
    command_allowlist: tuple[str, ...]
    mutation_allowlist: tuple[str, ...]
    required_checks: tuple[str, ...]
    token_scopes: tuple[str, ...]
    emergency_stop_source: str
    audit_store: str
    max_fix_iterations: int
    quarantine_enabled: bool
    one_active_job: bool = True
    unattended_scheduler_enabled: bool = False
    force_push_enabled: bool = False
    direct_main_writes_enabled: bool = False

    def canonical_payload(self) -> dict:
        return asdict(self)

    def digest(self) -> str:
        raw = json.dumps(self.canonical_payload(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class SignedReadinessReport:
    status: ReadinessStatus
    repository: str
    repository_sha: str
    operator: str
    issued_at: str
    expires_at: str
    configuration_digest: str
    gates: tuple[ReadinessGate, ...] = field(default_factory=tuple)
    unresolved_risks: tuple[str, ...] = field(default_factory=tuple)
    signature_algorithm: str = "hmac-sha256"
    signature: str = ""

    def signing_payload(self) -> dict:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload.pop("signature", None)
        return payload


class ReadinessProbe(Protocol):
    def evaluate(self, config: ReadinessConfig) -> tuple[ReadinessGate, ...]: ...


class ReadinessError(RuntimeError):
    pass


class ProductionReadinessGate:
    def __init__(self, probe: ReadinessProbe, signing_key: bytes):
        if not signing_key:
            raise ValueError("signing_key cannot be empty")
        self.probe = probe
        self.signing_key = signing_key

    def evaluate(self, config: ReadinessConfig, *, now: datetime | None = None) -> SignedReadinessReport:
        now = now or datetime.now(timezone.utc)
        gates = list(self._config_gates(config))
        gates.extend(self.probe.evaluate(config))
        status = ReadinessStatus.READY if all(gate.passed for gate in gates) else ReadinessStatus.NOT_READY
        unresolved = tuple(gate.name for gate in gates if not gate.passed)
        unsigned = SignedReadinessReport(
            status=status,
            repository=config.repository,
            repository_sha=config.repository_sha,
            operator=config.operator,
            issued_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=config.report_ttl_seconds)).isoformat(),
            configuration_digest=config.digest(),
            gates=tuple(gates),
            unresolved_risks=unresolved,
        )
        return SignedReadinessReport(**{**asdict(unsigned), "status": unsigned.status, "gates": unsigned.gates, "signature": self._sign(unsigned)})

    @staticmethod
    def _config_gates(config: ReadinessConfig) -> tuple[ReadinessGate, ...]:
        return (
            ReadinessGate("repository_identity", bool(config.repository), config.repository),
            ReadinessGate("repository_sha", bool(config.repository_sha), config.repository_sha),
            ReadinessGate("operator_identity", bool(config.operator), config.operator),
            ReadinessGate("bounded_report_ttl", 0 < config.report_ttl_seconds <= 86400, str(config.report_ttl_seconds)),
            ReadinessGate("path_allowlist", bool(config.path_allowlist)),
            ReadinessGate("command_allowlist", bool(config.command_allowlist)),
            ReadinessGate("mutation_allowlist", bool(config.mutation_allowlist)),
            ReadinessGate("required_checks", bool(config.required_checks)),
            ReadinessGate("token_scopes", bool(config.token_scopes)),
            ReadinessGate("emergency_stop_source", bool(config.emergency_stop_source)),
            ReadinessGate("audit_store", bool(config.audit_store)),
            ReadinessGate("bounded_fix_iterations", config.max_fix_iterations >= 0, str(config.max_fix_iterations)),
            ReadinessGate("quarantine_enabled", config.quarantine_enabled),
            ReadinessGate("one_active_job", config.one_active_job),
            ReadinessGate("unattended_scheduler_disabled", not config.unattended_scheduler_enabled),
            ReadinessGate("force_push_disabled", not config.force_push_enabled),
            ReadinessGate("direct_main_writes_disabled", not config.direct_main_writes_enabled),
        )

    def _sign(self, report: SignedReadinessReport) -> str:
        raw = json.dumps(report.signing_payload(), sort_keys=True, separators=(",", ":")).encode()
        return hmac.new(self.signing_key, raw, hashlib.sha256).hexdigest()

    def verify(
        self,
        report: SignedReadinessReport,
        config: ReadinessConfig,
        *,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now(timezone.utc)
        if report.status != ReadinessStatus.READY:
            raise ReadinessError("Readiness report is not READY")
        if report.repository != config.repository or report.repository_sha != config.repository_sha:
            raise ReadinessError("Readiness report repository state does not match")
        if report.configuration_digest != config.digest():
            raise ReadinessError("Readiness configuration digest does not match")
        if now >= datetime.fromisoformat(report.expires_at):
            raise ReadinessError("Readiness report has expired")
        expected = self._sign(SignedReadinessReport(**{**asdict(report), "status": report.status, "gates": report.gates, "signature": ""}))
        if not hmac.compare_digest(report.signature, expected):
            raise ReadinessError("Readiness report signature is invalid")


@dataclass(frozen=True)
class StaticReadinessProbe:
    gates: tuple[ReadinessGate, ...] = field(default_factory=tuple)

    def evaluate(self, config: ReadinessConfig) -> tuple[ReadinessGate, ...]:
        return self.gates
