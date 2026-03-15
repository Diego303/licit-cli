"""Tests for the architect connector."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from licit.config.schema import ConnectorArchitectConfig
from licit.connectors.architect import ArchitectConnector
from licit.connectors.base import Connector
from licit.core.evidence import EvidenceBundle

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def architect_project(tmp_path: Path) -> Path:
    """Create a project directory with architect data."""
    # Reports
    reports_dir = tmp_path / ".architect" / "reports"
    reports_dir.mkdir(parents=True)
    shutil.copy(FIXTURES / "architect_report.json", reports_dir / "task-001.json")
    shutil.copy(FIXTURES / "architect_report_2.json", reports_dir / "task-002.json")

    # Audit log
    shutil.copy(FIXTURES / "architect_audit.jsonl", tmp_path / ".architect" / "audit.jsonl")

    # Config
    shutil.copy(FIXTURES / "architect_config.yaml", tmp_path / ".architect" / "config.yaml")

    return tmp_path


def make_connector(
    root: Path,
    enabled: bool = True,
    reports_dir: str = ".architect/reports",
    audit_log: str | None = None,
    config_path: str | None = None,
) -> ArchitectConnector:
    """Helper to build an ArchitectConnector."""
    cfg = ConnectorArchitectConfig(
        enabled=enabled,
        reports_dir=reports_dir,
        audit_log=audit_log,
        config_path=config_path,
    )
    return ArchitectConnector(str(root), cfg)


class TestArchitectConnectorProtocol:
    """Verify ArchitectConnector satisfies the Connector protocol."""

    def test_implements_protocol(self, tmp_path: Path) -> None:
        conn = make_connector(tmp_path)
        assert isinstance(conn, Connector)

    def test_name_property(self, tmp_path: Path) -> None:
        conn = make_connector(tmp_path)
        assert conn.name == "architect"

    def test_enabled_property(self, tmp_path: Path) -> None:
        conn = make_connector(tmp_path, enabled=False)
        assert conn.enabled is False

    def test_available_no_data(self, tmp_path: Path) -> None:
        conn = make_connector(tmp_path)
        assert conn.available() is False


class TestArchitectReports:
    """Test reading architect report JSON files."""

    def test_reads_reports(self, architect_project: Path) -> None:
        conn = make_connector(architect_project)
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert result.files_read >= 2
        assert result.has_errors is False
        assert ev.has_audit_trail is True
        assert ev.audit_entry_count >= 2

    def test_empty_reports_dir(self, tmp_path: Path) -> None:
        (tmp_path / ".architect" / "reports").mkdir(parents=True)
        conn = make_connector(tmp_path)
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert result.files_read == 0
        assert ev.has_audit_trail is False

    def test_malformed_report_json(self, tmp_path: Path) -> None:
        reports_dir = tmp_path / ".architect" / "reports"
        reports_dir.mkdir(parents=True)
        (reports_dir / "bad.json").write_text("not json", encoding="utf-8")

        conn = make_connector(tmp_path)
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert len(result.errors) >= 1
        assert ev.has_audit_trail is False

    def test_report_with_non_object(self, tmp_path: Path) -> None:
        reports_dir = tmp_path / ".architect" / "reports"
        reports_dir.mkdir(parents=True)
        (reports_dir / "array.json").write_text("[1, 2, 3]", encoding="utf-8")

        conn = make_connector(tmp_path)
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert len(result.errors) >= 1


class TestArchitectAuditLog:
    """Test reading architect audit JSONL logs."""

    def test_reads_audit_log(self, architect_project: Path) -> None:
        conn = make_connector(
            architect_project,
            audit_log=".architect/audit.jsonl",
        )
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert result.has_errors is False
        assert ev.has_audit_trail is True
        # 2 reports + 6 audit entries
        assert ev.audit_entry_count >= 6

    def test_missing_audit_log(self, tmp_path: Path) -> None:
        conn = make_connector(
            tmp_path,
            audit_log=".architect/nonexistent.jsonl",
        )
        ev = EvidenceBundle()
        result = conn.collect(ev)
        assert result.has_errors is False  # Missing log is not a failure

    def test_audit_log_with_malformed_lines(self, tmp_path: Path) -> None:
        audit_path = tmp_path / "audit.jsonl"
        audit_path.write_text(
            '{"event": "ok", "timestamp": "2026-01-01T00:00:00Z"}\n'
            'not valid json\n'
            '{"event": "also_ok"}\n',
            encoding="utf-8",
        )
        conn = make_connector(tmp_path, audit_log="audit.jsonl")
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert ev.audit_entry_count >= 2
        assert len(result.errors) >= 1

    def test_empty_audit_log(self, tmp_path: Path) -> None:
        audit_path = tmp_path / "audit.jsonl"
        audit_path.write_text("", encoding="utf-8")
        conn = make_connector(tmp_path, audit_log="audit.jsonl")
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert result.has_errors is False
        assert result.files_read >= 1


class TestArchitectConfig:
    """Test reading architect config YAML."""

    def test_reads_guardrails(self, architect_project: Path) -> None:
        conn = make_connector(
            architect_project,
            config_path=".architect/config.yaml",
        )
        ev = EvidenceBundle()
        conn.collect(ev)

        assert ev.has_guardrails is True
        # 3 protected + 2 blocked + 2 code_rules = 7
        assert ev.guardrail_count == 7
        assert ev.has_quality_gates is True
        assert ev.quality_gate_count == 3

    def test_reads_budget(self, architect_project: Path) -> None:
        conn = make_connector(
            architect_project,
            config_path=".architect/config.yaml",
        )
        ev = EvidenceBundle()
        conn.collect(ev)

        assert ev.has_budget_limits is True

    def test_reads_dry_run_and_rollback(self, architect_project: Path) -> None:
        conn = make_connector(
            architect_project,
            config_path=".architect/config.yaml",
        )
        ev = EvidenceBundle()
        conn.collect(ev)

        assert ev.has_dry_run is True
        assert ev.has_rollback is True

    def test_missing_config(self, tmp_path: Path) -> None:
        conn = make_connector(tmp_path, config_path="does-not-exist.yaml")
        ev = EvidenceBundle()
        conn.collect(ev)

        assert ev.has_guardrails is False

    def test_config_not_a_dict(self, tmp_path: Path) -> None:
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("- just\n- a\n- list\n", encoding="utf-8")
        conn = make_connector(tmp_path, config_path="bad.yaml")
        ev = EvidenceBundle()
        conn.collect(ev)

        assert ev.has_guardrails is False

    def test_config_no_guardrails(self, tmp_path: Path) -> None:
        config_file = tmp_path / "minimal.yaml"
        config_file.write_text("model: gpt-4.1\n", encoding="utf-8")
        conn = make_connector(tmp_path, config_path="minimal.yaml")
        ev = EvidenceBundle()
        conn.collect(ev)

        assert ev.has_guardrails is False
        assert ev.has_dry_run is True  # default (not explicitly False)


class TestArchitectAvailability:
    """Test the available() check."""

    def test_available_with_reports(self, architect_project: Path) -> None:
        conn = make_connector(architect_project)
        assert conn.available() is True

    def test_available_with_config_only(self, tmp_path: Path) -> None:
        (tmp_path / ".architect").mkdir()
        (tmp_path / ".architect" / "config.yaml").write_text("model: x\n", encoding="utf-8")
        conn = make_connector(tmp_path, config_path=".architect/config.yaml")
        assert conn.available() is True

    def test_not_available(self, tmp_path: Path) -> None:
        conn = make_connector(tmp_path)
        assert conn.available() is False


class TestArchitectFullCollect:
    """Integration test: all three sources together."""

    def test_full_collect(self, architect_project: Path) -> None:
        conn = make_connector(
            architect_project,
            audit_log=".architect/audit.jsonl",
            config_path=".architect/config.yaml",
        )
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert result.success is True  # files_read > 0 and no errors
        # Reports (2) + audit (1 file) + config (1 file) = 4+ files read
        assert result.files_read >= 4
        assert ev.has_audit_trail is True
        assert ev.has_guardrails is True
        assert ev.has_budget_limits is True
        assert result.has_errors is False
