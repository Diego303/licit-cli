"""QA edge-case tests for Phase 7 connectors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from licit.config.schema import (
    ConnectorArchitectConfig,
    ConnectorVigilConfig,
    LicitConfig,
)
from licit.connectors.architect import ArchitectConnector
from licit.connectors.base import ConnectorResult
from licit.connectors.vigil import VigilConnector
from licit.core.evidence import EvidenceBundle, EvidenceCollector
from licit.core.project import CICDConfig, ProjectContext, SecurityTooling


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context(root_dir: str) -> ProjectContext:
    return ProjectContext(
        root_dir=root_dir,
        name="test",
        cicd=CICDConfig(platform="none"),
        security=SecurityTooling(),
    )


# ---------------------------------------------------------------------------
# ArchitectConnector edge cases
# ---------------------------------------------------------------------------

class TestArchitectEdgeCases:
    """Edge cases the happy-path tests don't cover."""

    def test_unicode_in_report_content(self, tmp_path: Path) -> None:
        """Reports with unicode characters (accents, CJK) should parse fine."""
        reports_dir = tmp_path / ".architect" / "reports"
        reports_dir.mkdir(parents=True)
        data = {"task_id": "tarea-ñ", "status": "完了", "model": "clàude"}
        (reports_dir / "uni.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8",
        )

        cfg = ConnectorArchitectConfig(enabled=True)
        conn = ArchitectConnector(str(tmp_path), cfg)
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert result.files_read == 1
        assert result.has_errors is False

    def test_yaml_config_only_whitespace(self, tmp_path: Path) -> None:
        """A YAML file with only whitespace should not crash."""
        cfg_file = tmp_path / "empty.yaml"
        cfg_file.write_text("   \n\n  \n", encoding="utf-8")

        cfg = ConnectorArchitectConfig(enabled=True, config_path="empty.yaml")
        conn = ArchitectConnector(str(tmp_path), cfg)
        ev = EvidenceBundle()
        conn.collect(ev)

        assert ev.has_guardrails is False
        assert ev.has_dry_run is False  # yaml.safe_load returns None → not a dict → early return

    def test_guardrail_count_additive(self, tmp_path: Path) -> None:
        """If guardrail_count already has a value, connector should add to it."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            "guardrails:\n  protected_files:\n    - .env\n    - .key\n",
            encoding="utf-8",
        )

        cfg = ConnectorArchitectConfig(enabled=True, config_path="config.yaml")
        conn = ArchitectConnector(str(tmp_path), cfg)
        ev = EvidenceBundle()
        ev.guardrail_count = 5  # Pre-existing count from another source

        conn.collect(ev)

        assert ev.guardrail_count == 7  # 5 + 2 new

    def test_audit_log_huge_line_count(self, tmp_path: Path) -> None:
        """Audit log with 500 lines should parse within reason."""
        lines = [
            json.dumps({"event": f"e{i}", "timestamp": "2026-01-01T00:00:00Z"})
            for i in range(500)
        ]
        audit = tmp_path / "big.jsonl"
        audit.write_text("\n".join(lines), encoding="utf-8")

        cfg = ConnectorArchitectConfig(enabled=True, audit_log="big.jsonl")
        conn = ArchitectConnector(str(tmp_path), cfg)
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert ev.audit_entry_count == 500
        assert result.has_errors is False

    def test_report_with_missing_optional_fields(self, tmp_path: Path) -> None:
        """A minimal report with just {} should not crash."""
        reports_dir = tmp_path / ".architect" / "reports"
        reports_dir.mkdir(parents=True)
        (reports_dir / "minimal.json").write_text("{}", encoding="utf-8")

        cfg = ConnectorArchitectConfig(enabled=True)
        conn = ArchitectConnector(str(tmp_path), cfg)
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert result.files_read == 1
        assert result.has_errors is False

    def test_config_path_none_uses_default(self, tmp_path: Path) -> None:
        """When config_path is None, should check .architect/config.yaml."""
        arch = tmp_path / ".architect"
        arch.mkdir()
        (arch / "config.yaml").write_text("model: test\n", encoding="utf-8")

        cfg = ConnectorArchitectConfig(enabled=True, config_path=None)
        conn = ArchitectConnector(str(tmp_path), cfg)
        ev = EvidenceBundle()
        result = conn.collect(ev)

        # Should read the default config path
        assert result.files_read >= 1

    def test_dry_run_explicitly_false(self, tmp_path: Path) -> None:
        """dry_run: false should mean has_dry_run is False."""
        cfg_file = tmp_path / "c.yaml"
        cfg_file.write_text("dry_run: false\nrollback: false\n", encoding="utf-8")

        cfg = ConnectorArchitectConfig(enabled=True, config_path="c.yaml")
        conn = ArchitectConnector(str(tmp_path), cfg)
        ev = EvidenceBundle()
        conn.collect(ev)

        assert ev.has_dry_run is False
        assert ev.has_rollback is False


# ---------------------------------------------------------------------------
# VigilConnector edge cases
# ---------------------------------------------------------------------------

class TestVigilEdgeCases:
    """Edge cases for SARIF parsing."""

    def test_sarif_100_findings(self, tmp_path: Path) -> None:
        """Verify connector scales to many findings without issue."""
        results_list = [
            {"ruleId": f"R{i}", "level": "warning", "message": {"text": f"Issue {i}"}}
            for i in range(100)
        ]
        sarif = {"version": "2.1.0", "runs": [
            {"tool": {"driver": {"name": "scanner"}}, "results": results_list},
        ]}
        (tmp_path / "big.sarif").write_text(json.dumps(sarif), encoding="utf-8")

        cfg = ConnectorVigilConfig(enabled=True, sarif_path="big.sarif")
        conn = VigilConnector(str(tmp_path), cfg)
        ev = EvidenceBundle()
        conn.collect(ev)

        assert ev.security_findings_total == 100
        assert ev.security_findings_high == 100

    def test_sarif_unicode_messages(self, tmp_path: Path) -> None:
        """SARIF with unicode in messages should parse."""
        sarif = {"version": "2.1.0", "runs": [
            {"tool": {"driver": {"name": "vigil"}}, "results": [
                {"ruleId": "V1", "level": "error",
                 "message": {"text": "Inyección de código — señal 警告"}},
            ]},
        ]}
        (tmp_path / "uni.sarif").write_text(
            json.dumps(sarif, ensure_ascii=False), encoding="utf-8",
        )

        cfg = ConnectorVigilConfig(enabled=True, sarif_path="uni.sarif")
        conn = VigilConnector(str(tmp_path), cfg)
        ev = EvidenceBundle()
        conn.collect(ev)

        assert ev.security_findings_total == 1

    def test_sarif_result_with_unknown_level(self, tmp_path: Path) -> None:
        """Unknown level should be counted as 'low'."""
        sarif = {"version": "2.1.0", "runs": [
            {"tool": {"driver": {"name": "tool"}}, "results": [
                {"ruleId": "X", "level": "custom-level", "message": {"text": "x"}},
            ]},
        ]}
        (tmp_path / "unk.sarif").write_text(json.dumps(sarif), encoding="utf-8")

        cfg = ConnectorVigilConfig(enabled=True, sarif_path="unk.sarif")
        conn = VigilConnector(str(tmp_path), cfg)
        ev = EvidenceBundle()
        conn.collect(ev)

        assert ev.security_findings_total == 1
        assert ev.security_findings_critical == 0
        assert ev.security_findings_high == 0

    def test_sarif_with_no_tool_section(self, tmp_path: Path) -> None:
        """Run without 'tool' key should still parse results."""
        sarif = {"version": "2.1.0", "runs": [
            {"results": [
                {"ruleId": "R1", "level": "error", "message": {"text": "bad"}},
            ]},
        ]}
        (tmp_path / "notool.sarif").write_text(json.dumps(sarif), encoding="utf-8")

        cfg = ConnectorVigilConfig(enabled=True, sarif_path="notool.sarif")
        conn = VigilConnector(str(tmp_path), cfg)
        ev = EvidenceBundle()
        conn.collect(ev)

        assert ev.security_findings_total == 1

    def test_sarif_path_is_directory_no_sarif_files(self, tmp_path: Path) -> None:
        """Directory with no .sarif files should read 0."""
        sarif_dir = tmp_path / "scans"
        sarif_dir.mkdir()
        (sarif_dir / "readme.txt").write_text("not a sarif", encoding="utf-8")

        cfg = ConnectorVigilConfig(enabled=True, sarif_path="scans")
        conn = VigilConnector(str(tmp_path), cfg)
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert result.files_read == 0
        assert ev.security_findings_total == 0

    def test_sbom_non_object(self, tmp_path: Path) -> None:
        """SBOM that is a JSON array, not object, should error."""
        (tmp_path / "sbom.json").write_text("[1,2,3]", encoding="utf-8")

        cfg = ConnectorVigilConfig(enabled=True, sbom_path="sbom.json")
        conn = VigilConnector(str(tmp_path), cfg)
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert result.has_errors is True

    def test_sarif_empty_runs_list(self, tmp_path: Path) -> None:
        """SARIF with runs: [] should count as a successful read."""
        sarif = {"version": "2.1.0", "runs": []}
        (tmp_path / "empty.sarif").write_text(json.dumps(sarif), encoding="utf-8")

        cfg = ConnectorVigilConfig(enabled=True, sarif_path="empty.sarif")
        conn = VigilConnector(str(tmp_path), cfg)
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert result.files_read == 1
        assert ev.security_findings_total == 0


# ---------------------------------------------------------------------------
# ConnectorResult edge cases
# ---------------------------------------------------------------------------

class TestConnectorResultEdgeCases:
    """Boundary conditions on the ConnectorResult dataclass."""

    def test_default_is_empty(self) -> None:
        r = ConnectorResult(connector_name="x")
        assert r.files_read == 0
        assert r.errors == []
        assert r.success is False  # No files read

    def test_errors_list_not_shared(self) -> None:
        """Two ConnectorResults should not share the same errors list."""
        r1 = ConnectorResult(connector_name="a")
        r2 = ConnectorResult(connector_name="b")
        r1.errors.append("oops")
        assert r2.errors == []


# ---------------------------------------------------------------------------
# EvidenceCollector + Connectors cross-module
# ---------------------------------------------------------------------------

class TestEvidenceConnectorCrossModule:
    """Verify connectors integrate correctly via EvidenceCollector."""

    def test_both_connectors_enabled(self, tmp_path: Path) -> None:
        """When both connectors enabled, both should contribute evidence."""
        # Architect
        reports = tmp_path / ".architect" / "reports"
        reports.mkdir(parents=True)
        (reports / "r.json").write_text('{"task_id": "t1"}', encoding="utf-8")
        (tmp_path / ".architect" / "config.yaml").write_text(
            "guardrails:\n  protected_files:\n    - .env\n", encoding="utf-8",
        )

        # SARIF
        sarif = {"version": "2.1.0", "runs": [
            {"tool": {"driver": {"name": "vigil"}}, "results": [
                {"ruleId": "V1", "level": "error", "message": {"text": "bad"}},
            ]},
        ]}
        (tmp_path / "scan.sarif").write_text(json.dumps(sarif), encoding="utf-8")

        config = LicitConfig()
        config.connectors.architect.enabled = True
        config.connectors.architect.config_path = ".architect/config.yaml"
        config.connectors.vigil.enabled = True

        ctx = _make_context(str(tmp_path))
        ctx.security.sarif_files = ["scan.sarif"]

        collector = EvidenceCollector(str(tmp_path), ctx, config)
        ev = collector.collect()

        assert ev.has_audit_trail is True
        assert ev.has_guardrails is True
        assert ev.security_findings_total == 1
        assert len(collector.connector_results) == 2

    def test_inline_path_no_architect_config_path(self, tmp_path: Path) -> None:
        """Inline path when context.architect_config_path is None should not crash."""
        ctx = _make_context(str(tmp_path))
        ctx.architect_config_path = None

        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()

        # Should complete without error, no guardrails
        assert ev.has_guardrails is False

    def test_inline_path_no_sarif_files(self, tmp_path: Path) -> None:
        """Inline path when no SARIF files exist should not crash."""
        ctx = _make_context(str(tmp_path))
        ctx.security.sarif_files = []

        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()

        assert ev.security_findings_total == 0


# ---------------------------------------------------------------------------
# CLI connect edge case
# ---------------------------------------------------------------------------

class TestConnectCLIEdgeCases:
    """CLI-level edge cases for the connect command."""

    def test_connect_invalid_connector_rejected(self) -> None:
        """licit connect with unknown connector should fail."""
        from click.testing import CliRunner

        from licit.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main, ["connect", "unknown"],
            obj={"config_path": None, "verbose": False},
        )
        assert result.exit_code != 0
        # Click should show an error about invalid choice
        assert "invalid" in result.output.lower() or "invalid" in (result.stderr or "").lower() \
            or "Usage" in result.output
