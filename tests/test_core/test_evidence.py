"""Tests for evidence collection."""

import json
from pathlib import Path

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
