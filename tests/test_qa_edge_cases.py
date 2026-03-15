"""QA edge case tests — Phase 1 hardening.

Tests that cover edge cases, boundary conditions, and integration
paths not covered by the original test suite.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from pydantic import ValidationError

from licit.cli import main
from licit.config.loader import load_config, save_config
from licit.config.schema import LicitConfig, ProvenanceConfig
from licit.core.evidence import EvidenceBundle, EvidenceCollector
from licit.core.models import (
    ChangeSeverity,
    ComplianceStatus,
    ComplianceSummary,
    ConfigChange,
    ControlRequirement,
    ControlResult,
    GapItem,
    ProvenanceRecord,
    ProvenanceSource,
)
from licit.core.project import (
    AgentConfigFile,
    CICDConfig,
    ProjectContext,
    ProjectDetector,
    SecurityTooling,
)


# ──────────────────────────────────────────────
# Config Schema — edge cases
# ──────────────────────────────────────────────


class TestConfigValidation:
    """Tests for config validation edge cases."""

    def test_confidence_threshold_too_high_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProvenanceConfig(confidence_threshold=1.5)

    def test_confidence_threshold_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProvenanceConfig(confidence_threshold=-0.1)

    def test_confidence_threshold_boundary_zero(self) -> None:
        config = ProvenanceConfig(confidence_threshold=0.0)
        assert config.confidence_threshold == 0.0

    def test_confidence_threshold_boundary_one(self) -> None:
        config = ProvenanceConfig(confidence_threshold=1.0)
        assert config.confidence_threshold == 1.0

    def test_extra_fields_ignored(self) -> None:
        data = {
            "frameworks": {"eu_ai_act": True, "unknown_field": "value"},
            "nonexistent_section": {"foo": "bar"},
        }
        config = LicitConfig.model_validate(data)
        assert config.frameworks.eu_ai_act is True

    def test_empty_yaml_returns_defaults(self, tmp_path: Path) -> None:
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("", encoding="utf-8")
        config = load_config(str(config_file))
        # yaml.safe_load("") returns None → not a dict → defaults
        assert config.frameworks.eu_ai_act is True

    def test_yaml_with_null_value(self, tmp_path: Path) -> None:
        config_file = tmp_path / "null.yaml"
        config_file.write_text("provenance:\n  sign_key_path: null\n", encoding="utf-8")
        config = load_config(str(config_file))
        assert config.provenance.sign_key_path is None

    def test_unicode_in_config_values(self, tmp_path: Path) -> None:
        config_file = tmp_path / "unicode.yaml"
        config_file.write_text(
            'fria:\n  organization: "Ñoño Corp"\n  system_name: "系统"\n',
            encoding="utf-8",
        )
        config = load_config(str(config_file))
        assert config.fria.organization == "Ñoño Corp"
        assert config.fria.system_name == "系统"

    def test_save_and_load_preserves_unicode(self, tmp_path: Path) -> None:
        config = LicitConfig()
        config.fria.organization = "Ünïcödé Cörp"
        path = save_config(config, str(tmp_path / ".licit.yaml"))
        loaded = load_config(str(path))
        assert loaded.fria.organization == "Ünïcödé Cörp"

    def test_invalid_confidence_in_yaml_returns_defaults(self, tmp_path: Path) -> None:
        config_file = tmp_path / "bad_thresh.yaml"
        config_file.write_text(
            "provenance:\n  confidence_threshold: 5.0\n", encoding="utf-8"
        )
        config = load_config(str(config_file))
        # Validation fails → falls back to defaults
        assert config.provenance.confidence_threshold == 0.6


# ──────────────────────────────────────────────
# Core Models — enum and dataclass edge cases
# ──────────────────────────────────────────────


class TestCoreModels:
    """Tests for core model enums and dataclasses."""

    def test_compliance_status_values(self) -> None:
        assert ComplianceStatus.COMPLIANT == "compliant"
        assert ComplianceStatus.NON_COMPLIANT == "non-compliant"
        assert ComplianceStatus.NOT_EVALUATED == "not-evaluated"

    def test_compliance_status_membership(self) -> None:
        assert "compliant" in ComplianceStatus.__members__.values()
        assert ComplianceStatus("partial") == ComplianceStatus.PARTIAL

    def test_compliance_status_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            ComplianceStatus("invalid")

    def test_change_severity_ordering(self) -> None:
        assert ChangeSeverity.MAJOR == "major"
        assert ChangeSeverity.MINOR == "minor"
        assert ChangeSeverity.PATCH == "patch"

    def test_provenance_source_all_values(self) -> None:
        expected = {"git-infer", "session-log", "git-ai", "manual", "connector"}
        actual = {s.value for s in ProvenanceSource}
        assert actual == expected

    def test_provenance_record_minimal(self) -> None:
        from datetime import datetime

        record = ProvenanceRecord(
            file_path="test.py",
            source="ai",
            confidence=0.9,
            method=ProvenanceSource.GIT_INFER,
            timestamp=datetime.now(),
        )
        assert record.lines_range is None
        assert record.model is None
        assert record.signature is None

    def test_provenance_record_full(self) -> None:
        from datetime import datetime

        record = ProvenanceRecord(
            file_path="src/app.py",
            source="mixed",
            confidence=0.7,
            method=ProvenanceSource.SESSION_LOG,
            timestamp=datetime.now(),
            lines_range=(10, 50),
            model="claude-sonnet-4",
            agent_tool="claude-code",
            session_id="abc123",
            cost_usd=0.05,
        )
        assert record.lines_range == (10, 50)
        assert record.cost_usd == 0.05

    def test_control_result_default_recommendations_empty(self) -> None:
        req = ControlRequirement(
            id="TEST-1", framework="test", name="Test", description="Test"
        )
        result = ControlResult(
            requirement=req,
            status=ComplianceStatus.COMPLIANT,
            evidence="test evidence",
        )
        assert result.recommendations == []
        assert result.source == "auto"

    def test_gap_item_defaults(self) -> None:
        req = ControlRequirement(
            id="GAP-1", framework="test", name="Gap", description="A gap"
        )
        gap = GapItem(
            requirement=req,
            status=ComplianceStatus.NON_COMPLIANT,
            gap_description="Missing",
            recommendation="Fix it",
            effort="low",
        )
        assert gap.tools_suggested == []
        assert gap.priority == 0

    def test_compliance_summary_fields(self) -> None:
        summary = ComplianceSummary(
            framework="eu-ai-act",
            total_controls=10,
            compliant=5,
            partial=2,
            non_compliant=1,
            not_applicable=1,
            not_evaluated=1,
            compliance_rate=62.5,
        )
        assert summary.compliance_rate == 62.5

    def test_config_change_fields(self) -> None:
        from datetime import datetime

        change = ConfigChange(
            file_path="CLAUDE.md",
            field_path="model",
            old_value="sonnet",
            new_value="opus",
            severity=ChangeSeverity.MAJOR,
            description="Model changed",
            timestamp=datetime.now(),
        )
        assert change.commit_sha is None


# ──────────────────────────────────────────────
# ProjectDetector — edge cases
# ──────────────────────────────────────────────


class TestProjectDetectorEdgeCases:
    """Edge case tests for ProjectDetector."""

    def test_both_pyproject_and_package_json_prefers_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "python-app"\n', encoding="utf-8"
        )
        (tmp_path / "package.json").write_text(
            '{"name": "js-app"}', encoding="utf-8"
        )
        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))
        assert ctx.name == "python-app"

    def test_rust_project_detection(self, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "my-crate"\n', encoding="utf-8"
        )
        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))
        assert "rust" in ctx.languages
        assert "cargo" in ctx.package_managers

    def test_java_maven_detection(self, tmp_path: Path) -> None:
        (tmp_path / "pom.xml").write_text("<project></project>", encoding="utf-8")
        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))
        assert "java" in ctx.languages
        assert "maven" in ctx.package_managers

    def test_java_gradle_detection(self, tmp_path: Path) -> None:
        (tmp_path / "build.gradle").write_text("apply plugin: 'java'\n", encoding="utf-8")
        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))
        assert "java" in ctx.languages
        assert "gradle" in ctx.package_managers

    def test_malformed_pyproject_toml(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("not valid toml [[[", encoding="utf-8")
        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))
        # Should not crash — falls back to directory name
        assert ctx.name == tmp_path.name
        assert "python" in ctx.languages  # pyproject.toml exists → language detected

    def test_malformed_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{invalid json", encoding="utf-8")
        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))
        assert ctx.name == tmp_path.name
        assert "javascript" in ctx.languages

    def test_multiple_cicd_detects_first(self, tmp_path: Path) -> None:
        """Only the first matching CI/CD platform is detected."""
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
        (tmp_path / ".gitlab-ci.yml").write_text("stages:\n", encoding="utf-8")

        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))
        assert ctx.cicd.platform == "github-actions"

    def test_pyproject_without_project_section(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 100\n", encoding="utf-8"
        )
        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))
        assert ctx.name == tmp_path.name  # No name found → directory name
        assert "python" in ctx.languages

    def test_package_json_with_no_name(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            '{"version": "1.0.0"}', encoding="utf-8"
        )
        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))
        assert ctx.name == tmp_path.name

    def test_sarif_files_detected(self, tmp_path: Path) -> None:
        (tmp_path / "results.sarif").write_text("{}", encoding="utf-8")
        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))
        assert "results.sarif" in ctx.security.sarif_files

    def test_codeql_detection(self, tmp_path: Path) -> None:
        (tmp_path / ".github" / "codeql").mkdir(parents=True)
        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))
        assert ctx.security.has_codeql is True

    def test_snyk_detection(self, tmp_path: Path) -> None:
        (tmp_path / ".snyk").write_text("{}", encoding="utf-8")
        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))
        assert ctx.security.has_snyk is True

    def test_copilot_config_detection(self, tmp_path: Path) -> None:
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "copilot-instructions.md").write_text(
            "# Instructions\n", encoding="utf-8"
        )
        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))
        types = {c.agent_type for c in ctx.agent_configs}
        assert "copilot" in types

    def test_multiple_agent_configs(self, tmp_path: Path) -> None:
        (tmp_path / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")
        (tmp_path / ".cursorrules").write_text("rules\n", encoding="utf-8")
        (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")

        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))
        assert len(ctx.agent_configs) == 3


# ──────────────────────────────────────────────
# EvidenceCollector — edge cases
# ──────────────────────────────────────────────


class TestEvidenceCollectorEdgeCases:
    """Edge case tests for EvidenceCollector."""

    def _make_context(
        self,
        root_dir: str,
        cicd: str = "none",
        architect_config_path: str | None = None,
    ) -> ProjectContext:
        return ProjectContext(
            root_dir=root_dir,
            name="test",
            cicd=CICDConfig(platform=cicd),
            security=SecurityTooling(),
            architect_config_path=architect_config_path,
        )

    def test_provenance_jsonl_exists_with_malformed_data(self, tmp_path: Path) -> None:
        """provenance.jsonl exists with malformed records — stats show zero."""
        licit_dir = tmp_path / ".licit"
        licit_dir.mkdir()
        (licit_dir / "provenance.jsonl").write_text(
            '{"file_path":"test.py"}\n', encoding="utf-8"
        )
        ctx = self._make_context(str(tmp_path))
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()
        assert ev.has_provenance is True  # File exists
        assert ev.provenance_stats["total_files"] == 0  # Malformed records skipped

    def test_malformed_architect_config(self, tmp_path: Path) -> None:
        architect_dir = tmp_path / ".architect"
        architect_dir.mkdir()
        (architect_dir / "config.yaml").write_text(
            "{{not valid yaml", encoding="utf-8"
        )
        ctx = self._make_context(
            str(tmp_path), architect_config_path=".architect/config.yaml"
        )
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()
        assert ev.has_guardrails is False

    def test_architect_config_not_a_dict(self, tmp_path: Path) -> None:
        architect_dir = tmp_path / ".architect"
        architect_dir.mkdir()
        (architect_dir / "config.yaml").write_text(
            "- item1\n- item2\n", encoding="utf-8"
        )
        ctx = self._make_context(
            str(tmp_path), architect_config_path=".architect/config.yaml"
        )
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()
        assert ev.has_guardrails is False

    def test_architect_config_empty_guardrails(self, tmp_path: Path) -> None:
        architect_dir = tmp_path / ".architect"
        architect_dir.mkdir()
        (architect_dir / "config.yaml").write_text(
            yaml.dump({"guardrails": {}}), encoding="utf-8"
        )
        ctx = self._make_context(
            str(tmp_path), architect_config_path=".architect/config.yaml"
        )
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()
        assert ev.has_guardrails is False  # Empty guardrails dict → falsy

    def test_sarif_non_vigil_tool_also_counted(self, tmp_path: Path) -> None:
        """SARIF findings from any tool are counted, not just vigil."""
        sarif_data = {
            "runs": [{
                "tool": {"driver": {"name": "semgrep"}},
                "results": [{"level": "error", "message": {"text": "finding"}}],
            }]
        }
        (tmp_path / "scan.sarif").write_text(json.dumps(sarif_data), encoding="utf-8")
        ctx = self._make_context(str(tmp_path))
        ctx.security.sarif_files = ["scan.sarif"]
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()
        assert ev.security_findings_total == 1  # All SARIF tools counted
        assert ev.security_findings_critical == 1

    def test_sarif_malformed_json(self, tmp_path: Path) -> None:
        (tmp_path / "bad.sarif").write_text("{not json", encoding="utf-8")
        ctx = self._make_context(str(tmp_path))
        ctx.security.sarif_files = ["bad.sarif"]
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()
        assert ev.security_findings_total == 0

    def test_sarif_missing_file(self, tmp_path: Path) -> None:
        ctx = self._make_context(str(tmp_path))
        ctx.security.sarif_files = ["nonexistent.sarif"]
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()
        assert ev.security_findings_total == 0

    def test_changelog_with_h3_headers_not_counted(self, tmp_path: Path) -> None:
        """Only ## headers should be counted, not ### or deeper."""
        licit_dir = tmp_path / ".licit"
        licit_dir.mkdir()
        content = "## v2\nChanges\n### Details\nMore\n## v1\nOld\n#### Deep\n"
        (licit_dir / "changelog.md").write_text(content, encoding="utf-8")
        ctx = self._make_context(str(tmp_path))
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()
        assert ev.changelog_entry_count == 2  # Only ## lines, not ### or ####

    def test_empty_licit_directory(self, tmp_path: Path) -> None:
        (tmp_path / ".licit").mkdir()
        ctx = self._make_context(str(tmp_path))
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()
        assert ev.has_provenance is False
        assert ev.has_fria is False
        assert ev.has_annex_iv is False
        assert ev.has_changelog is False

    def test_architect_dry_run_rollback_defaults(self, tmp_path: Path) -> None:
        """Architect config without explicit dry_run/rollback → both True."""
        architect_dir = tmp_path / ".architect"
        architect_dir.mkdir()
        (architect_dir / "config.yaml").write_text(
            yaml.dump({"guardrails": {"protected_files": ["x"]}}),
            encoding="utf-8",
        )
        ctx = self._make_context(
            str(tmp_path), architect_config_path=".architect/config.yaml"
        )
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()
        assert ev.has_dry_run is True
        assert ev.has_rollback is True

    def test_architect_dry_run_explicitly_disabled(self, tmp_path: Path) -> None:
        architect_dir = tmp_path / ".architect"
        architect_dir.mkdir()
        (architect_dir / "config.yaml").write_text(
            yaml.dump({
                "guardrails": {"protected_files": ["x"]},
                "dry_run": False,
                "rollback": False,
            }),
            encoding="utf-8",
        )
        ctx = self._make_context(
            str(tmp_path), architect_config_path=".architect/config.yaml"
        )
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()
        assert ev.has_dry_run is False
        assert ev.has_rollback is False


# ──────────────────────────────────────────────
# CLI — edge cases and integration
# ──────────────────────────────────────────────


class TestCLIEdgeCases:
    """Edge case tests for CLI commands."""

    def test_connect_persists_change_to_yaml(self, tmp_path: Path) -> None:
        """Verify connect actually writes the enabled state to disk."""
        config_file = tmp_path / ".licit.yaml"
        config_file.write_text(
            yaml.dump({"connectors": {"architect": {"enabled": False}}}),
            encoding="utf-8",
        )
        runner = CliRunner()
        runner.invoke(
            main,
            ["--config", str(config_file), "connect", "architect", "--enable"],
            catch_exceptions=False,
        )
        reloaded = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        assert reloaded["connectors"]["architect"]["enabled"] is True

    def test_connect_disable_persists(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".licit.yaml"
        config_file.write_text(
            yaml.dump({"connectors": {"vigil": {"enabled": True}}}),
            encoding="utf-8",
        )
        runner = CliRunner()
        runner.invoke(
            main,
            ["--config", str(config_file), "connect", "vigil", "--disable"],
            catch_exceptions=False,
        )
        reloaded = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        assert reloaded["connectors"]["vigil"]["enabled"] is False

    def test_status_with_config_file(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".licit.yaml"
        save_config(LicitConfig(), str(config_file))
        original = os.getcwd()
        try:
            os.chdir(tmp_path)
            runner = CliRunner()
            result = runner.invoke(main, ["status"], catch_exceptions=False)
            assert result.exit_code == 0
            assert ".licit.yaml" in result.output
        finally:
            os.chdir(original)

    def test_init_then_status_integration(self, tmp_path: Path) -> None:
        """End-to-end: init creates config, status reads it."""
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "T"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        (tmp_path / "README.md").write_text("# Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path, capture_output=True, check=True,
        )

        original = os.getcwd()
        try:
            os.chdir(tmp_path)
            runner = CliRunner()

            # Init
            result = runner.invoke(main, ["init"], catch_exceptions=False)
            assert result.exit_code == 0
            assert (tmp_path / ".licit.yaml").exists()

            # Status should find the config
            result = runner.invoke(main, ["status"], catch_exceptions=False)
            assert result.exit_code == 0
            assert ".licit.yaml" in result.output
            assert "[x] EU AI Act" in result.output
        finally:
            os.chdir(original)

    def test_invalid_framework_choice(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["init", "--framework", "invalid"])
        assert result.exit_code != 0

    def test_help_all_commands_have_description(self) -> None:
        runner = CliRunner()
        commands = [
            "init", "trace", "changelog", "fria", "annex-iv",
            "report", "gaps", "verify", "status", "connect",
        ]
        for cmd in commands:
            result = runner.invoke(main, [cmd, "--help"])
            assert result.exit_code == 0, f"{cmd} --help failed"
            # All commands should have some description text
            assert len(result.output) > 50, f"{cmd} help output too short"

    def test_verbose_flag_accepted(self, tmp_path: Path) -> None:
        original = os.getcwd()
        try:
            os.chdir(tmp_path)
            runner = CliRunner()
            result = runner.invoke(main, ["-v", "status"], catch_exceptions=False)
            assert result.exit_code == 0
        finally:
            os.chdir(original)


# ──────────────────────────────────────────────
# Import safety — no circular imports
# ──────────────────────────────────────────────


class TestImportSafety:
    """Verify no circular imports between modules."""

    def test_import_config_schema(self) -> None:
        from licit.config import schema  # noqa: F401

    def test_import_config_loader(self) -> None:
        from licit.config import loader  # noqa: F401

    def test_import_core_models(self) -> None:
        from licit.core import models  # noqa: F401

    def test_import_core_project(self) -> None:
        from licit.core import project  # noqa: F401

    def test_import_core_evidence(self) -> None:
        from licit.core import evidence  # noqa: F401

    def test_import_cli(self) -> None:
        from licit import cli  # noqa: F401

    def test_import_logging(self) -> None:
        from licit.logging import setup  # noqa: F401

    def test_version_exists(self) -> None:
        from licit import __version__
        assert isinstance(__version__, str)
        assert "." in __version__
