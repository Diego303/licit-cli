"""Architect connector — reads reports, audit logs, and config from architect.

architect is an AI coding agent that produces structured reports, audit JSONL
logs, and a config YAML with guardrails / quality gates / budget controls.
This connector reads those outputs and enriches the EvidenceBundle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
import yaml

from licit.config.schema import ConnectorArchitectConfig
from licit.connectors.base import ConnectorResult

if TYPE_CHECKING:
    from licit.core.evidence import EvidenceBundle

logger = structlog.get_logger()


@dataclass
class ArchitectReport:
    """Parsed summary of a single architect report file."""

    path: str
    task_id: str | None = None
    status: str | None = None
    model: str | None = None
    cost_usd: float | None = None
    files_changed: list[str] = field(default_factory=list)
    timestamp: str | None = None


@dataclass
class AuditEntry:
    """A single entry from architect's audit JSONL log."""

    event: str
    timestamp: str | None = None
    details: dict[str, object] = field(default_factory=dict)


class ArchitectConnector:
    """Reads architect reports, audit logs, and config to enrich evidence."""

    name = "architect"

    def __init__(self, root_dir: str, config: ConnectorArchitectConfig) -> None:
        self.root = Path(root_dir)
        self.config = config

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def available(self) -> bool:
        """Check if architect outputs exist on disk."""
        reports_dir = self.root / self.config.reports_dir
        config_path = self.root / (self.config.config_path or ".architect/config.yaml")
        return reports_dir.exists() or config_path.exists()

    def collect(self, evidence: EvidenceBundle) -> ConnectorResult:
        """Read all architect data and enrich the evidence bundle."""
        result = ConnectorResult(connector_name=self.name)

        self._read_reports(evidence, result)
        self._read_audit_log(evidence, result)
        self._read_config(evidence, result)

        logger.info(
            "architect_connector_collected",
            files_read=result.files_read,
            errors=len(result.errors),
        )
        return result

    def _read_reports(self, evidence: EvidenceBundle, result: ConnectorResult) -> None:
        """Read architect JSON reports from reports_dir."""
        reports_dir = self.root / self.config.reports_dir
        if not reports_dir.exists():
            return

        reports: list[ArchitectReport] = []
        for report_file in sorted(reports_dir.glob("*.json")):
            try:
                data = json.loads(report_file.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    result.errors.append(f"{report_file.name}: not a JSON object")
                    continue

                reports.append(ArchitectReport(
                    path=str(report_file.relative_to(self.root)),
                    task_id=data.get("task_id") if isinstance(data.get("task_id"), str) else None,
                    status=data.get("status") if isinstance(data.get("status"), str) else None,
                    model=data.get("model") if isinstance(data.get("model"), str) else None,
                    cost_usd=(
                        float(data["cost_usd"])
                        if isinstance(data.get("cost_usd"), (int, float))
                        else None
                    ),
                    files_changed=(
                        data["files_changed"]
                        if isinstance(data.get("files_changed"), list)
                        else []
                    ),
                    timestamp=(
                        data["timestamp"]
                        if isinstance(data.get("timestamp"), str)
                        else None
                    ),
                ))
                result.files_read += 1

            except (json.JSONDecodeError, OSError) as exc:
                result.errors.append(f"{report_file.name}: {exc}")
                logger.debug("architect_report_parse_error", file=str(report_file), error=str(exc))

        if reports:
            evidence.has_audit_trail = True
            evidence.audit_entry_count += len(reports)

    def _read_audit_log(self, evidence: EvidenceBundle, result: ConnectorResult) -> None:
        """Read architect audit JSONL log."""
        audit_path_str = self.config.audit_log
        if not audit_path_str:
            return

        audit_path = self.root / audit_path_str
        if not audit_path.exists():
            return

        entries: list[AuditEntry] = []
        try:
            for raw_line in audit_path.read_text(encoding="utf-8").splitlines():
                stripped = raw_line.strip()
                if not stripped:
                    continue
                try:
                    data = json.loads(stripped)
                    if not isinstance(data, dict):
                        continue
                    entries.append(AuditEntry(
                        event=data.get("event", "unknown") if isinstance(
                            data.get("event"), str
                        ) else "unknown",
                        timestamp=data.get("timestamp") if isinstance(
                            data.get("timestamp"), str
                        ) else None,
                        details={
                            k: v for k, v in data.items()
                            if k not in ("event", "timestamp")
                        },
                    ))
                except json.JSONDecodeError:
                    result.errors.append("audit log: malformed line")
                    continue

            result.files_read += 1

        except OSError as exc:
            result.errors.append(f"audit log: {exc}")
            logger.debug("architect_audit_read_error", error=str(exc))
            return

        if entries:
            evidence.has_audit_trail = True
            evidence.audit_entry_count += len(entries)

    def _read_config(self, evidence: EvidenceBundle, result: ConnectorResult) -> None:
        """Read architect config YAML for guardrails, quality gates, budget."""
        config_path_str = self.config.config_path or ".architect/config.yaml"
        config_path = self.root / config_path_str
        if not config_path.exists():
            return

        try:
            data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return

            result.files_read += 1

            # Guardrails
            guardrails = data.get("guardrails", {})
            if isinstance(guardrails, dict) and guardrails:
                evidence.has_guardrails = True
                evidence.guardrail_count += (
                    len(guardrails.get("protected_files") or [])
                    + len(guardrails.get("blocked_commands") or [])
                    + len(guardrails.get("code_rules") or [])
                )

                quality_gates = guardrails.get("quality_gates")
                if quality_gates and isinstance(quality_gates, list):
                    evidence.has_quality_gates = True
                    evidence.quality_gate_count = len(quality_gates)

            # Budget limits
            costs = data.get("costs", {})
            if isinstance(costs, dict) and costs.get("budget_usd"):
                evidence.has_budget_limits = True

            # Capabilities
            if data.get("dry_run") is not False:
                evidence.has_dry_run = True
            if data.get("rollback") is not False:
                evidence.has_rollback = True

        except (yaml.YAMLError, OSError) as exc:
            result.errors.append(f"config: {exc}")
            logger.debug("architect_config_parse_error", error=str(exc))
