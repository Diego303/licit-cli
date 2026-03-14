"""Tests for the Annex IV generator."""

from __future__ import annotations

from pathlib import Path

import pytest

from licit.core.evidence import EvidenceBundle
from licit.core.project import AgentConfigFile, SecurityTooling
from licit.frameworks.eu_ai_act.annex_iv import AnnexIVGenerator
from tests.conftest import make_context, make_evidence


@pytest.fixture
def generator() -> AnnexIVGenerator:
    ctx = make_context(
        name="my-project",
        languages=["python", "typescript"],
        agent_configs=[
            AgentConfigFile(path="CLAUDE.md", agent_type="claude-code"),
            AgentConfigFile(path=".cursorrules", agent_type="cursor"),
        ],
        has_architect=True,
        git_initialized=True,
        total_commits=200,
        security=SecurityTooling(has_vigil=True, has_semgrep=True),
    )
    ctx.frameworks = ["fastapi"]
    ctx.package_managers = ["pip", "npm"]
    ctx.test_framework = "pytest"
    ctx.test_dirs = ["tests"]
    ctx.total_contributors = 5
    ev = EvidenceBundle(
        has_provenance=True,
        provenance_stats={"ai_percentage": 35.0},
        has_audit_trail=True,
        audit_entry_count=42,
        has_guardrails=True,
        guardrail_count=8,
        has_quality_gates=True,
        quality_gate_count=3,
        has_budget_limits=True,
        has_human_review_gate=True,
        has_fria=True,
        has_changelog=True,
    )
    return AnnexIVGenerator(ctx, ev)


# ── Generation ─────────────────────────────────────────────────────


class TestGenerate:
    def test_creates_file(self, generator: AnnexIVGenerator, tmp_path: Path) -> None:
        output = str(tmp_path / "annex-iv.md")
        generator.generate(output, organization="ACME Corp", product_name="WebApp")
        assert Path(output).exists()

    def test_creates_parent_dirs(
        self, generator: AnnexIVGenerator, tmp_path: Path
    ) -> None:
        output = str(tmp_path / "sub" / "dir" / "annex-iv.md")
        generator.generate(output, organization="Org", product_name="Prod")
        assert Path(output).exists()

    def test_content_has_header(
        self, generator: AnnexIVGenerator, tmp_path: Path
    ) -> None:
        output = str(tmp_path / "annex-iv.md")
        generator.generate(output, organization="ACME Corp", product_name="WebApp")
        content = Path(output).read_text(encoding="utf-8")
        assert "Annex IV" in content
        assert "Technical Documentation" in content
        assert "ACME Corp" in content
        assert "WebApp" in content


# ── Content sections ───────────────────────────────────────────────


class TestContentSections:
    @pytest.fixture(autouse=True)
    def _generate(self, generator: AnnexIVGenerator, tmp_path: Path) -> None:
        self.output = str(tmp_path / "annex-iv.md")
        generator.generate(self.output, organization="TestOrg", product_name="TestProd")
        self.content = Path(self.output).read_text(encoding="utf-8")

    def test_general_description_section(self) -> None:
        assert "General Description" in self.content
        assert "my-project" in self.content

    def test_languages_listed(self) -> None:
        assert "python" in self.content
        assert "typescript" in self.content

    def test_frameworks_listed(self) -> None:
        assert "fastapi" in self.content

    def test_agent_types_listed(self) -> None:
        assert "claude-code" in self.content
        assert "cursor" in self.content

    def test_architect_mentioned(self) -> None:
        assert "architect" in self.content.lower()

    def test_development_process_section(self) -> None:
        assert "Development Process" in self.content
        assert "200" in self.content  # total_commits

    def test_provenance_info(self) -> None:
        assert "35.0%" in self.content

    def test_cicd_section(self) -> None:
        assert "CI/CD" in self.content

    def test_risk_management_section(self) -> None:
        assert "Risk Management" in self.content
        assert "8 guardrail rules" in self.content
        assert "3 quality gates" in self.content

    def test_testing_section(self) -> None:
        assert "pytest" in self.content

    def test_security_tools_listed(self) -> None:
        assert "vigil" in self.content
        assert "Semgrep" in self.content

    def test_human_oversight_mentioned(self) -> None:
        assert "Human review" in self.content or "human review" in self.content


# ── Minimal project ───────────────────────────────────────────────


class TestMinimalProject:
    def test_generates_without_any_features(self, tmp_path: Path) -> None:
        """Even a bare project should produce valid output."""
        ctx = make_context(
            name="bare-project",
            languages=[],
            agent_configs=[],
            has_architect=False,
            git_initialized=False,
            total_commits=0,
        )
        ev = make_evidence()
        gen = AnnexIVGenerator(ctx, ev)
        output = str(tmp_path / "annex-iv.md")
        gen.generate(output, organization="Org", product_name="Prod")
        content = Path(output).read_text(encoding="utf-8")
        assert "Annex IV" in content
        assert "bare-project" in content
        assert "No version control detected" in content

    def test_recommendations_shown_for_missing_features(
        self, tmp_path: Path
    ) -> None:
        ctx = make_context(
            name="incomplete",
            agent_configs=[],
            git_initialized=True,
            total_commits=10,
        )
        ev = make_evidence()
        gen = AnnexIVGenerator(ctx, ev)
        output = str(tmp_path / "annex-iv.md")
        gen.generate(output, organization="Org", product_name="Prod")
        content = Path(output).read_text(encoding="utf-8")
        assert "Recommendation" in content
