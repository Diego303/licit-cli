"""Tests for the FRIA generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from licit.core.evidence import EvidenceBundle
from licit.core.project import AgentConfigFile, SecurityTooling
from licit.frameworks.eu_ai_act.fria import FRIA_STEPS, FRIAGenerator
from tests.conftest import make_context, make_evidence


@pytest.fixture
def generator() -> FRIAGenerator:
    ctx = make_context(
        agent_configs=[AgentConfigFile(path="CLAUDE.md", agent_type="claude-code")],
        has_architect=True,
        git_initialized=True,
        total_commits=100,
    )
    ev = make_evidence(
        has_guardrails=True,
        guardrail_count=5,
        has_quality_gates=True,
        quality_gate_count=2,
        has_budget_limits=True,
        has_audit_trail=True,
        has_human_review_gate=True,
        has_provenance=True,
    )
    return FRIAGenerator(ctx, ev)


# ── FRIA Steps structure ──────────────────────────────────────────


class TestFRIASteps:
    def test_has_five_steps(self) -> None:
        assert len(FRIA_STEPS) == 5

    def test_steps_have_required_keys(self) -> None:
        for step in FRIA_STEPS:
            assert "id" in step
            assert "title" in step
            assert "description" in step
            assert "questions" in step
            assert isinstance(step["questions"], list)
            assert len(step["questions"]) > 0

    def test_questions_have_required_keys(self) -> None:
        for step in FRIA_STEPS:
            for q in step["questions"]:
                assert "id" in q
                assert "question" in q
                assert "field" in q
                assert "type" in q
                assert q["type"] in ("text", "choice")

    def test_choice_questions_have_choices(self) -> None:
        for step in FRIA_STEPS:
            for q in step["questions"]:
                if q["type"] == "choice":
                    assert "choices" in q
                    assert len(q["choices"]) >= 2

    def test_unique_field_names(self) -> None:
        fields: list[str] = []
        for step in FRIA_STEPS:
            for q in step["questions"]:
                fields.append(q["field"])
        assert len(fields) == len(set(fields)), "Duplicate field names in FRIA steps"


# ── Auto-detection ─────────────────────────────────────────────────


class TestAutoDetect:
    def test_detect_system_purpose_with_architect(
        self, generator: FRIAGenerator
    ) -> None:
        result = generator._auto_detect("system_purpose")
        assert result is not None
        assert "architect" in result.lower()

    def test_detect_system_purpose_with_agent_configs(self) -> None:
        ctx = make_context(
            agent_configs=[
                AgentConfigFile(path="CLAUDE.md", agent_type="claude-code"),
            ],
            has_architect=False,
        )
        ev = make_evidence()
        gen = FRIAGenerator(ctx, ev)
        result = gen._auto_detect("system_purpose")
        assert result is not None
        assert "claude-code" in result

    def test_detect_system_purpose_none_without_configs(self) -> None:
        ctx = make_context(agent_configs=[], has_architect=False)
        ev = make_evidence()
        gen = FRIAGenerator(ctx, ev)
        result = gen._auto_detect("system_purpose")
        assert result is None

    def test_detect_ai_technology_headless(self, generator: FRIAGenerator) -> None:
        result = generator._auto_detect("ai_technology")
        assert result is not None
        assert "headless" in result.lower()

    def test_detect_ai_technology_interactive(self) -> None:
        ctx = make_context(
            agent_configs=[AgentConfigFile(path="CLAUDE.md", agent_type="claude-code")],
            has_architect=False,
        )
        ev = make_evidence()
        gen = FRIAGenerator(ctx, ev)
        result = gen._auto_detect("ai_technology")
        assert result == "AI coding assistant (interactive)"

    def test_detect_human_review(self, generator: FRIAGenerator) -> None:
        result = generator._auto_detect("human_review")
        assert result is not None
        assert "human review" in result.lower()

    def test_detect_human_review_none_without_gate(self) -> None:
        ctx = make_context()
        ev = make_evidence(has_human_review_gate=False)
        gen = FRIAGenerator(ctx, ev)
        assert gen._auto_detect("human_review") is None

    def test_detect_guardrails(self, generator: FRIAGenerator) -> None:
        result = generator._auto_detect("guardrails")
        assert result is not None
        assert "5 guardrail rules" in result
        assert "quality gates" in result
        assert "budget limits" in result

    def test_detect_security_scanning_none(self) -> None:
        ctx = make_context()
        ev = make_evidence()
        gen = FRIAGenerator(ctx, ev)
        assert gen._auto_detect("security_scanning") is None

    def test_detect_security_scanning_with_tools(self) -> None:
        ctx = make_context(security=SecurityTooling(has_vigil=True, has_semgrep=True))
        ev = make_evidence()
        gen = FRIAGenerator(ctx, ev)
        result = gen._auto_detect("security_scanning")
        assert result is not None
        assert "vigil" in result
        assert "Semgrep" in result

    def test_detect_testing(self) -> None:
        from licit.core.project import ProjectContext

        ctx = make_context()
        ctx.test_framework = "pytest"
        ctx.test_dirs = ["tests"]
        ev = make_evidence()
        gen = FRIAGenerator(ctx, ev)
        result = gen._auto_detect("testing")
        assert result is not None
        assert "pytest" in result

    def test_detect_audit_trail(self, generator: FRIAGenerator) -> None:
        result = generator._auto_detect("audit_trail")
        assert result is not None
        assert "Git history" in result
        assert "provenance" in result.lower()

    def test_detect_unknown_field_returns_none(
        self, generator: FRIAGenerator
    ) -> None:
        assert generator._auto_detect("nonexistent_field") is None


# ── Report generation ──────────────────────────────────────────────


class TestReportGeneration:
    def test_generate_report_creates_file(
        self, generator: FRIAGenerator, tmp_path: Path
    ) -> None:
        responses: dict[str, Any] = {
            "system_purpose": "Test AI system",
            "project_name": "test-project",
            "licit_version": "0.3.0",
        }
        output = str(tmp_path / "fria-report.md")
        generator.generate_report(responses, output)
        assert Path(output).exists()

    def test_generate_report_contains_content(
        self, generator: FRIAGenerator, tmp_path: Path
    ) -> None:
        responses: dict[str, Any] = {
            "system_purpose": "Test AI system for compliance",
            "project_name": "test-project",
            "licit_version": "0.3.0",
            "risk_level": "Minimal",
        }
        output = str(tmp_path / "fria-report.md")
        generator.generate_report(responses, output)
        content = Path(output).read_text(encoding="utf-8")
        assert "Fundamental Rights Impact Assessment" in content
        assert "Article 27" in content
        assert "Test AI system for compliance" in content

    def test_generate_report_creates_parent_dirs(
        self, generator: FRIAGenerator, tmp_path: Path
    ) -> None:
        output = str(tmp_path / "sub" / "dir" / "fria-report.md")
        responses: dict[str, Any] = {"project_name": "test", "licit_version": "0.3.0"}
        generator.generate_report(responses, output)
        assert Path(output).exists()


# ── Data saving ────────────────────────────────────────────────────


class TestSaveData:
    def test_save_data_creates_json(
        self, generator: FRIAGenerator, tmp_path: Path
    ) -> None:
        import json

        responses: dict[str, Any] = {"field": "value", "number": 42}
        data_path = str(tmp_path / "fria-data.json")
        generator.save_data(responses, data_path)
        assert Path(data_path).exists()
        loaded = json.loads(Path(data_path).read_text(encoding="utf-8"))
        assert loaded["field"] == "value"
        assert loaded["number"] == 42

    def test_save_data_creates_parent_dirs(
        self, generator: FRIAGenerator, tmp_path: Path
    ) -> None:
        data_path = str(tmp_path / "nested" / "dir" / "data.json")
        generator.save_data({"key": "val"}, data_path)
        assert Path(data_path).exists()
