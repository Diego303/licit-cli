"""Tests for evidence collection."""

import json
from pathlib import Path

from licit.config.schema import LicitConfig
from licit.connectors.base import ConnectorResult
from licit.core.evidence import EvidenceBundle, EvidenceCollector
from licit.core.project import CICDConfig, ProjectContext, SecurityTooling


class TestEvidenceBundle:
    """Tests for the EvidenceBundle dataclass."""

    def test_default_bundle_is_empty(self) -> None:
        ev = EvidenceBundle()
        assert ev.has_provenance is False
        assert ev.has_fria is False
        assert ev.has_guardrails is False
        assert ev.security_findings_total == 0

    def test_bundle_with_values(self) -> None:
        ev = EvidenceBundle(
            has_provenance=True,
            has_fria=True,
            fria_path=".licit/fria-data.json",
            has_guardrails=True,
            guardrail_count=5,
        )
        assert ev.has_provenance is True
        assert ev.guardrail_count == 5
        assert ev.fria_path == ".licit/fria-data.json"


class TestEvidenceCollector:
    """Tests for EvidenceCollector."""

    def _make_context(self, root_dir: str) -> ProjectContext:
        return ProjectContext(
            root_dir=root_dir,
            name="test",
            cicd=CICDConfig(platform="none"),
            security=SecurityTooling(),
        )

    def test_collect_empty_project(self, tmp_path: Path) -> None:
        ctx = self._make_context(str(tmp_path))
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()

        assert ev.has_provenance is False
        assert ev.has_fria is False
        assert ev.has_changelog is False

    def test_collect_detects_fria(self, tmp_path: Path) -> None:
        licit_dir = tmp_path / ".licit"
        licit_dir.mkdir()
        (licit_dir / "fria-data.json").write_text('{"test": true}', encoding="utf-8")

        ctx = self._make_context(str(tmp_path))
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()

        assert ev.has_fria is True
        assert ev.fria_path is not None

    def test_collect_detects_annex_iv(self, tmp_path: Path) -> None:
        licit_dir = tmp_path / ".licit"
        licit_dir.mkdir()
        (licit_dir / "annex-iv.md").write_text("# Annex IV\n", encoding="utf-8")

        ctx = self._make_context(str(tmp_path))
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()

        assert ev.has_annex_iv is True

    def test_collect_detects_changelog(self, tmp_path: Path) -> None:
        licit_dir = tmp_path / ".licit"
        licit_dir.mkdir()
        (licit_dir / "changelog.md").write_text(
            "## v1\nChange 1\n## v2\nChange 2\n", encoding="utf-8"
        )

        ctx = self._make_context(str(tmp_path))
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()

        assert ev.has_changelog is True
        assert ev.changelog_entry_count == 2

    def test_collect_github_actions_implies_review_gate(self, tmp_path: Path) -> None:
        ctx = self._make_context(str(tmp_path))
        ctx.cicd = CICDConfig(platform="github-actions")

        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()

        assert ev.has_human_review_gate is True

    def test_collect_no_cicd_no_review_gate(self, tmp_path: Path) -> None:
        ctx = self._make_context(str(tmp_path))
        ctx.cicd = CICDConfig(platform="none")

        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()

        assert ev.has_human_review_gate is False

    def test_collect_architect_reports(self, tmp_path: Path) -> None:
        reports_dir = tmp_path / ".architect" / "reports"
        reports_dir.mkdir(parents=True)
        (reports_dir / "report1.json").write_text("{}", encoding="utf-8")
        (reports_dir / "report2.json").write_text("{}", encoding="utf-8")

        ctx = self._make_context(str(tmp_path))
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()

        assert ev.has_audit_trail is True
        assert ev.audit_entry_count == 2

    def test_collect_architect_config_guardrails(self, tmp_path: Path) -> None:
        import yaml

        architect_dir = tmp_path / ".architect"
        architect_dir.mkdir()
        config_data = {
            "guardrails": {
                "protected_files": ["LICENSE", "README.md"],
                "blocked_commands": ["rm -rf /"],
                "code_rules": ["no eval()"],
                "quality_gates": ["lint", "test"],
            },
            "costs": {"budget_usd": 50},
        }
        (architect_dir / "config.yaml").write_text(
            yaml.dump(config_data), encoding="utf-8"
        )

        ctx = self._make_context(str(tmp_path))
        ctx.architect_config_path = ".architect/config.yaml"

        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()

        assert ev.has_guardrails is True
        assert ev.guardrail_count == 4  # 2 protected_files + 1 blocked_command + 1 code_rule
        assert ev.has_quality_gates is True
        assert ev.quality_gate_count == 2
        assert ev.has_budget_limits is True

    def test_collect_vigil_sarif(self, tmp_path: Path) -> None:
        sarif_data = {
            "runs": [
                {
                    "tool": {"driver": {"name": "vigil-scanner"}},
                    "results": [
                        {"level": "error", "message": {"text": "Critical finding"}},
                        {"level": "warning", "message": {"text": "High finding"}},
                        {"level": "note", "message": {"text": "Info"}},
                    ],
                }
            ]
        }
        (tmp_path / "results.sarif").write_text(
            json.dumps(sarif_data), encoding="utf-8"
        )

        ctx = self._make_context(str(tmp_path))
        ctx.security.sarif_files = ["results.sarif"]

        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()

        assert ev.security_findings_total == 3
        assert ev.security_findings_critical == 1
        assert ev.security_findings_high == 1

    def test_collect_sarif_non_vigil_tool(self, tmp_path: Path) -> None:
        """SARIF from non-vigil tools should also be counted (inline path)."""
        sarif_data = {
            "runs": [
                {
                    "tool": {"driver": {"name": "semgrep"}},
                    "results": [
                        {"level": "error", "message": {"text": "SQL injection"}},
                    ],
                }
            ]
        }
        (tmp_path / "semgrep.sarif").write_text(
            json.dumps(sarif_data), encoding="utf-8"
        )

        ctx = self._make_context(str(tmp_path))
        ctx.security.sarif_files = ["semgrep.sarif"]

        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()

        assert ev.security_findings_total == 1
        assert ev.security_findings_critical == 1


class TestEvidenceCollectorWithConnectors:
    """Tests for EvidenceCollector when config with connectors is provided."""

    def _make_context(self, root_dir: str) -> ProjectContext:
        return ProjectContext(
            root_dir=root_dir,
            name="test",
            cicd=CICDConfig(platform="none"),
            security=SecurityTooling(),
        )

    def test_delegates_to_architect_connector(self, tmp_path: Path) -> None:
        """With config + architect enabled, connector should run."""
        # Set up architect data
        reports_dir = tmp_path / ".architect" / "reports"
        reports_dir.mkdir(parents=True)
        (reports_dir / "task-001.json").write_text(
            '{"task_id": "t1", "status": "completed"}', encoding="utf-8",
        )
        config_file = tmp_path / ".architect" / "config.yaml"
        config_file.write_text(
            "guardrails:\n  protected_files:\n    - .env\n", encoding="utf-8",
        )

        config = LicitConfig()
        config.connectors.architect.enabled = True
        config.connectors.architect.config_path = ".architect/config.yaml"

        ctx = self._make_context(str(tmp_path))
        collector = EvidenceCollector(str(tmp_path), ctx, config)
        ev = collector.collect()

        assert ev.has_audit_trail is True
        assert ev.has_guardrails is True
        assert len(collector.connector_results) >= 1
        assert collector.connector_results[0].connector_name == "architect"

    def test_disabled_connector_falls_back_to_inline(self, tmp_path: Path) -> None:
        """With config but connector disabled, inline path should run."""
        reports_dir = tmp_path / ".architect" / "reports"
        reports_dir.mkdir(parents=True)
        (reports_dir / "task-001.json").write_text("{}", encoding="utf-8")

        config = LicitConfig()
        config.connectors.architect.enabled = False

        ctx = self._make_context(str(tmp_path))
        collector = EvidenceCollector(str(tmp_path), ctx, config)
        ev = collector.collect()

        # Inline detects reports
        assert ev.has_audit_trail is True
        # No connector ran
        assert len(collector.connector_results) == 0

    def test_no_config_falls_back_to_inline(self, tmp_path: Path) -> None:
        """Without config, inline path should run (backwards compat)."""
        reports_dir = tmp_path / ".architect" / "reports"
        reports_dir.mkdir(parents=True)
        (reports_dir / "task-001.json").write_text("{}", encoding="utf-8")

        ctx = self._make_context(str(tmp_path))
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()

        assert ev.has_audit_trail is True
        assert len(collector.connector_results) == 0

    def test_connector_results_reset_each_collect(self, tmp_path: Path) -> None:
        """connector_results should be fresh on each collect() call."""
        config = LicitConfig()
        config.connectors.architect.enabled = True

        ctx = self._make_context(str(tmp_path))
        collector = EvidenceCollector(str(tmp_path), ctx, config)

        collector.collect()
        first_results = collector.connector_results
        collector.collect()
        second_results = collector.connector_results

        assert len(first_results) == len(second_results)


class TestConnectorResultComputed:
    """Test ConnectorResult.success computed property."""

    def test_success_when_files_read_no_errors(self) -> None:
        r = ConnectorResult(connector_name="test", files_read=3)
        assert r.success is True
        assert r.has_errors is False

    def test_not_success_when_no_files_read(self) -> None:
        r = ConnectorResult(connector_name="test")
        assert r.success is False

    def test_not_success_when_errors(self) -> None:
        r = ConnectorResult(connector_name="test", files_read=1, errors=["bad"])
        assert r.success is False
        assert r.has_errors is True

    def test_not_success_when_only_errors(self) -> None:
        r = ConnectorResult(connector_name="test", errors=["fail"])
        assert r.success is False
