"""QA edge-case and regression tests for Phase 4 — EU AI Act Framework.

Covers: Protocol conformance, unicode handling, empty inputs, boundary
values, template safety, round-trip data integrity, CLI integration,
and cross-module interactions that developer tests missed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from licit.core.evidence import EvidenceBundle
from licit.core.models import ComplianceStatus, ControlResult
from licit.core.project import AgentConfigFile, SecurityTooling
from licit.frameworks.base import ComplianceFramework
from licit.frameworks.eu_ai_act.annex_iv import AnnexIVGenerator
from licit.frameworks.eu_ai_act.evaluator import EUAIActEvaluator, _score_to_status
from licit.frameworks.eu_ai_act.fria import FRIA_STEPS, FRIAGenerator
from licit.frameworks.eu_ai_act.requirements import (
    REQUIREMENTS,
    get_requirement,
    get_requirements_by_category,
)
from licit.frameworks.registry import FrameworkRegistry
from tests.conftest import make_context, make_evidence


# ═══════════════════════════════════════════════════════════════════
# 1. Protocol conformance
# ═══════════════════════════════════════════════════════════════════


class TestProtocolConformance:
    """Verify EUAIActEvaluator satisfies the ComplianceFramework Protocol."""

    def test_isinstance_check(self) -> None:
        """runtime_checkable Protocol must accept the evaluator."""
        evaluator = EUAIActEvaluator()
        assert isinstance(evaluator, ComplianceFramework)

    def test_evaluate_signature_matches_protocol(self) -> None:
        """evaluate() must accept ProjectContext + EvidenceBundle and return list."""
        evaluator = EUAIActEvaluator()
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, ControlResult)

    def test_get_requirements_returns_control_requirements(self) -> None:
        from licit.core.models import ControlRequirement

        evaluator = EUAIActEvaluator()
        reqs = evaluator.get_requirements()
        for req in reqs:
            assert isinstance(req, ControlRequirement)


# ═══════════════════════════════════════════════════════════════════
# 2. _score_to_status boundary testing
# ═══════════════════════════════════════════════════════════════════


class TestScoreToStatus:
    def test_zero_score(self) -> None:
        assert _score_to_status(0, compliant_at=3, partial_at=1) == ComplianceStatus.NON_COMPLIANT

    def test_at_partial_boundary(self) -> None:
        assert _score_to_status(1, compliant_at=3, partial_at=1) == ComplianceStatus.PARTIAL

    def test_between_partial_and_compliant(self) -> None:
        assert _score_to_status(2, compliant_at=3, partial_at=1) == ComplianceStatus.PARTIAL

    def test_at_compliant_boundary(self) -> None:
        assert _score_to_status(3, compliant_at=3, partial_at=1) == ComplianceStatus.COMPLIANT

    def test_above_compliant(self) -> None:
        assert _score_to_status(99, compliant_at=3, partial_at=1) == ComplianceStatus.COMPLIANT

    def test_negative_score(self) -> None:
        assert _score_to_status(-1, compliant_at=3, partial_at=1) == ComplianceStatus.NON_COMPLIANT

    def test_partial_equals_compliant(self) -> None:
        """When partial_at == compliant_at, there's no PARTIAL band."""
        assert _score_to_status(2, compliant_at=3, partial_at=3) == ComplianceStatus.NON_COMPLIANT
        assert _score_to_status(3, compliant_at=3, partial_at=3) == ComplianceStatus.COMPLIANT


# ═══════════════════════════════════════════════════════════════════
# 3. Evaluator edge cases
# ═══════════════════════════════════════════════════════════════════


class TestEvaluatorEdgeCases:
    def test_provenance_stats_with_string_value(self) -> None:
        """Non-numeric ai_percentage should fallback gracefully to 0."""
        evaluator = EUAIActEvaluator()
        ctx = make_context(git_initialized=True)
        ev = make_evidence(
            has_provenance=True,
            provenance_stats={"ai_percentage": "not-a-number"},
        )
        results = evaluator.evaluate(ctx, ev)
        art12 = _find(results, "ART-12-1")
        assert "0%" in art12.evidence

    def test_provenance_stats_with_none_value(self) -> None:
        evaluator = EUAIActEvaluator()
        ctx = make_context()
        ev = make_evidence(
            has_provenance=True,
            provenance_stats={"ai_percentage": None},
        )
        results = evaluator.evaluate(ctx, ev)
        art12 = _find(results, "ART-12-1")
        assert "0%" in art12.evidence

    def test_provenance_stats_missing_key(self) -> None:
        evaluator = EUAIActEvaluator()
        ctx = make_context()
        ev = make_evidence(has_provenance=True, provenance_stats={})
        results = evaluator.evaluate(ctx, ev)
        art12 = _find(results, "ART-12-1")
        assert "0%" in art12.evidence

    def test_all_compliant_scenario(self) -> None:
        """A project with everything configured should be mostly compliant."""
        evaluator = EUAIActEvaluator()
        ctx = make_context(
            agent_configs=[AgentConfigFile(path="CLAUDE.md", agent_type="claude-code")],
            git_initialized=True,
            total_commits=500,
            security=SecurityTooling(has_vigil=True, has_semgrep=True),
        )
        ev = make_evidence(
            has_provenance=True,
            provenance_stats={"ai_percentage": 40},
            has_fria=True,
            fria_path=".licit/fria-data.json",
            has_annex_iv=True,
            annex_iv_path=".licit/annex-iv.md",
            has_guardrails=True,
            guardrail_count=15,
            has_quality_gates=True,
            quality_gate_count=5,
            has_budget_limits=True,
            has_audit_trail=True,
            audit_entry_count=100,
            has_human_review_gate=True,
            has_changelog=True,
            changelog_entry_count=20,
            has_dry_run=True,
            has_rollback=True,
        )
        results = evaluator.evaluate(ctx, ev)
        compliant = [r for r in results if r.status == ComplianceStatus.COMPLIANT]
        # Most should be compliant — Art 10 is always PARTIAL
        assert len(compliant) >= 9

    def test_all_non_compliant_scenario(self) -> None:
        """A bare project with nothing should have mostly non-compliant results."""
        evaluator = EUAIActEvaluator()
        ctx = make_context(
            agent_configs=[],
            git_initialized=False,
            total_commits=0,
        )
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        non_compliant = [r for r in results if r.status == ComplianceStatus.NON_COMPLIANT]
        assert len(non_compliant) >= 4

    def test_delegating_methods_preserve_caller_requirement(self) -> None:
        """Art 14(4)(a) delegates to Art 14(1) but should keep its own requirement ID."""
        evaluator = EUAIActEvaluator()
        ctx = make_context()
        ev = make_evidence(has_human_review_gate=True)
        results = evaluator.evaluate(ctx, ev)
        art14_4a = _find(results, "ART-14-4a")
        assert art14_4a.requirement.id == "ART-14-4a"
        assert art14_4a.requirement.name == "Human Oversight — Understand Capabilities"

    def test_art_26_5_delegates_with_correct_requirement(self) -> None:
        evaluator = EUAIActEvaluator()
        ctx = make_context(git_initialized=True)
        ev = make_evidence(has_audit_trail=True, audit_entry_count=5)
        results = evaluator.evaluate(ctx, ev)
        art26_5 = _find(results, "ART-26-5")
        assert art26_5.requirement.id == "ART-26-5"

    def test_recommendations_are_actionable_strings(self) -> None:
        """All recommendations should be non-empty strings."""
        evaluator = EUAIActEvaluator()
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        for r in results:
            for rec in r.recommendations:
                assert isinstance(rec, str)
                assert len(rec) > 5, f"Recommendation too short: {rec!r}"


# ═══════════════════════════════════════════════════════════════════
# 4. FRIA edge cases
# ═══════════════════════════════════════════════════════════════════


class TestFRIAEdgeCases:
    def test_generate_report_with_empty_responses(self, tmp_path: Path) -> None:
        """Template should handle completely empty responses dict."""
        ctx = make_context()
        ev = make_evidence()
        gen = FRIAGenerator(ctx, ev)
        output = str(tmp_path / "report.md")
        gen.generate_report({}, output)
        content = Path(output).read_text(encoding="utf-8")
        assert "Fundamental Rights Impact Assessment" in content
        assert "*Not provided*" in content

    def test_generate_report_with_unicode_responses(self, tmp_path: Path) -> None:
        """Unicode in responses should render correctly."""
        ctx = make_context()
        ev = make_evidence()
        gen = FRIAGenerator(ctx, ev)
        responses: dict[str, Any] = {
            "system_purpose": "Sistema de IA para análisis de código con acentos y ñ",
            "project_name": "proyecto-español",
            "licit_version": "0.3.0",
            "responsible_person": "José García — CTO",
        }
        output = str(tmp_path / "report.md")
        gen.generate_report(responses, output)
        content = Path(output).read_text(encoding="utf-8")
        assert "análisis" in content
        assert "José García" in content

    def test_save_load_roundtrip(self, tmp_path: Path) -> None:
        """Data saved with save_data should load back identically."""
        ctx = make_context()
        ev = make_evidence()
        gen = FRIAGenerator(ctx, ev)
        original: dict[str, Any] = {
            "system_purpose": "Test system",
            "risk_level": "Minimal",
            "number_field": 42,
        }
        data_path = str(tmp_path / "data.json")
        gen.save_data(original, data_path)
        loaded = json.loads(Path(data_path).read_text(encoding="utf-8"))
        assert loaded == original

    def test_detect_models_used_with_real_yaml(self, tmp_path: Path) -> None:
        """_detect_models_used should read model from architect config YAML."""
        config_path = tmp_path / ".architect" / "config.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(
            "llm:\n  model: claude-sonnet-4\n  provider: anthropic\n",
            encoding="utf-8",
        )
        ctx = make_context(
            root_dir=str(tmp_path),
            architect_config_path=".architect/config.yaml",
            has_architect=True,
        )
        ev = make_evidence()
        gen = FRIAGenerator(ctx, ev)
        result = gen._auto_detect("models_used")
        assert result is not None
        assert "claude-sonnet-4" in result

    def test_detect_models_used_with_malformed_yaml(self, tmp_path: Path) -> None:
        """Malformed YAML should return None, not crash."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("{{invalid yaml:::}", encoding="utf-8")
        ctx = make_context(
            root_dir=str(tmp_path),
            architect_config_path="config.yaml",
            has_architect=True,
        )
        ev = make_evidence()
        gen = FRIAGenerator(ctx, ev)
        result = gen._auto_detect("models_used")
        assert result is None

    def test_detect_models_used_with_missing_file(self, tmp_path: Path) -> None:
        """Missing config file should return None, not crash."""
        ctx = make_context(
            root_dir=str(tmp_path),
            architect_config_path="nonexistent.yaml",
            has_architect=True,
        )
        ev = make_evidence()
        gen = FRIAGenerator(ctx, ev)
        result = gen._auto_detect("models_used")
        assert result is None

    def test_detect_models_used_yaml_without_llm_key(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text("other_key: value\n", encoding="utf-8")
        ctx = make_context(
            root_dir=str(tmp_path),
            architect_config_path="config.yaml",
        )
        ev = make_evidence()
        gen = FRIAGenerator(ctx, ev)
        result = gen._auto_detect("models_used")
        assert result is None

    def test_fria_steps_question_ids_are_sequential(self) -> None:
        """Question IDs should follow step.question pattern (1.1, 1.2, ...)."""
        for step in FRIA_STEPS:
            for q in step["questions"]:
                qid: str = q["id"]
                assert qid.startswith(f"{step['id']}.")


# ═══════════════════════════════════════════════════════════════════
# 5. Annex IV edge cases
# ═══════════════════════════════════════════════════════════════════


class TestAnnexIVEdgeCases:
    def test_unicode_in_organization_and_product(self, tmp_path: Path) -> None:
        ctx = make_context(name="日本語プロジェクト")
        ev = make_evidence()
        gen = AnnexIVGenerator(ctx, ev)
        output = str(tmp_path / "annex.md")
        gen.generate(output, organization="Ünïcödé Org GmbH", product_name="Ñoño App")
        content = Path(output).read_text(encoding="utf-8")
        assert "Ünïcödé Org GmbH" in content
        assert "Ñoño App" in content
        assert "日本語プロジェクト" in content

    def test_empty_string_inputs(self, tmp_path: Path) -> None:
        """Empty org/product should not crash template rendering."""
        ctx = make_context()
        ev = make_evidence()
        gen = AnnexIVGenerator(ctx, ev)
        output = str(tmp_path / "annex.md")
        gen.generate(output, organization="", product_name="")
        content = Path(output).read_text(encoding="utf-8")
        assert "Annex IV" in content

    def test_pipe_in_organization_table_row(self, tmp_path: Path) -> None:
        """Pipe character in org name could break Markdown table — verify behavior."""
        ctx = make_context()
        ev = make_evidence()
        gen = AnnexIVGenerator(ctx, ev)
        output = str(tmp_path / "annex.md")
        gen.generate(output, organization="Org|With|Pipes", product_name="Prod")
        content = Path(output).read_text(encoding="utf-8")
        # Template does NOT escape pipes — this is a known limitation.
        # Document the behavior: the table row will be broken.
        assert "Org|With|Pipes" in content

    def test_provenance_percentage_zero(self, tmp_path: Path) -> None:
        ctx = make_context()
        ev = make_evidence(has_provenance=True, provenance_stats={"ai_percentage": 0})
        gen = AnnexIVGenerator(ctx, ev)
        output = str(tmp_path / "annex.md")
        gen.generate(output, organization="Org", product_name="Prod")
        content = Path(output).read_text(encoding="utf-8")
        assert "0.0%" in content

    def test_provenance_percentage_hundred(self, tmp_path: Path) -> None:
        ctx = make_context()
        ev = make_evidence(has_provenance=True, provenance_stats={"ai_percentage": 100.0})
        gen = AnnexIVGenerator(ctx, ev)
        output = str(tmp_path / "annex.md")
        gen.generate(output, organization="Org", product_name="Prod")
        content = Path(output).read_text(encoding="utf-8")
        assert "100.0%" in content


# ═══════════════════════════════════════════════════════════════════
# 6. Registry tests
# ═══════════════════════════════════════════════════════════════════


class TestFrameworkRegistry:
    def test_register_and_get(self) -> None:
        reg = FrameworkRegistry()
        evaluator = EUAIActEvaluator()
        reg.register(evaluator)
        retrieved = reg.get("eu-ai-act")
        assert retrieved is not None
        assert retrieved.name == "eu-ai-act"

    def test_get_missing_returns_none(self) -> None:
        reg = FrameworkRegistry()
        assert reg.get("nonexistent") is None

    def test_list_all(self) -> None:
        reg = FrameworkRegistry()
        reg.register(EUAIActEvaluator())
        assert len(reg.list_all()) == 1

    def test_names(self) -> None:
        reg = FrameworkRegistry()
        reg.register(EUAIActEvaluator())
        assert reg.names() == ["eu-ai-act"]

    def test_empty_registry(self) -> None:
        reg = FrameworkRegistry()
        assert reg.list_all() == []
        assert reg.names() == []


# ═══════════════════════════════════════════════════════════════════
# 7. CLI integration for Phase 4
# ═══════════════════════════════════════════════════════════════════


class TestCLIIntegration:
    def test_verify_eu_ai_act_runs(self, tmp_path: Path) -> None:
        """licit verify --framework eu-ai-act should produce output and exit non-zero."""
        import os

        from licit.cli import main

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # No .licit.yaml → uses defaults. No FRIA or Annex IV → non-compliant.
            result = runner.invoke(main, ["verify", "--framework", "eu-ai-act"], obj={})
            assert result.exit_code in (1, 2)
            assert "Compliance Verification" in result.output

    def test_verify_exit_codes_meaning(self, tmp_path: Path) -> None:
        """Exit code 1 = non-compliant, 2 = partial."""
        from licit.cli import main

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["verify", "--framework", "eu-ai-act"], obj={})
            # Without FRIA and Annex IV, at least ART-27-1 and ANNEX-IV are non-compliant
            assert result.exit_code == 1
            assert "Non-compliant" in result.output


# ═══════════════════════════════════════════════════════════════════
# 8. Requirements data integrity
# ═══════════════════════════════════════════════════════════════════


class TestRequirementsIntegrity:
    def test_all_requirement_ids_have_evaluator_method(self) -> None:
        """Every requirement should have a corresponding _eval_* method."""
        evaluator = EUAIActEvaluator()
        for req in REQUIREMENTS:
            method_name = f"_eval_{req.id.lower().replace('-', '_')}"
            method = getattr(evaluator, method_name, None)
            assert method is not None, (
                f"Missing evaluator method {method_name} for requirement {req.id}"
            )

    def test_requirement_frameworks_consistent(self) -> None:
        for req in REQUIREMENTS:
            assert req.framework == "eu-ai-act"

    def test_no_duplicate_categories(self) -> None:
        """Categories should be from a known set."""
        valid = {
            "risk-management",
            "data-governance",
            "record-keeping",
            "transparency",
            "human-oversight",
            "deployer-obligations",
            "fria",
            "documentation",
        }
        for req in REQUIREMENTS:
            assert req.category in valid, f"{req.id} has unknown category {req.category}"


# ═══════════════════════════════════════════════════════════════════
# 9. Cross-module interaction
# ═══════════════════════════════════════════════════════════════════


class TestCrossModule:
    def test_evaluator_results_compatible_with_gap_item(self) -> None:
        """ControlResult from evaluator should be usable to construct GapItem."""
        from licit.core.models import GapItem

        evaluator = EUAIActEvaluator()
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        non_compliant = [r for r in results if r.status == ComplianceStatus.NON_COMPLIANT]
        assert len(non_compliant) > 0
        # Verify we can construct a GapItem from a result
        r = non_compliant[0]
        gap = GapItem(
            requirement=r.requirement,
            status=r.status,
            gap_description=r.evidence,
            recommendation=r.recommendations[0] if r.recommendations else "N/A",
            effort="medium",
        )
        assert gap.requirement.id == r.requirement.id

    def test_evaluator_results_compatible_with_compliance_summary(self) -> None:
        """Results should allow computing ComplianceSummary."""
        from licit.core.models import ComplianceSummary

        evaluator = EUAIActEvaluator()
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        compliant = sum(1 for r in results if r.status == ComplianceStatus.COMPLIANT)
        partial = sum(1 for r in results if r.status == ComplianceStatus.PARTIAL)
        non_c = sum(1 for r in results if r.status == ComplianceStatus.NON_COMPLIANT)
        na = sum(1 for r in results if r.status == ComplianceStatus.NOT_APPLICABLE)
        ne = sum(1 for r in results if r.status == ComplianceStatus.NOT_EVALUATED)
        evaluated = len(results) - na - ne
        rate = (compliant / max(evaluated, 1)) * 100
        summary = ComplianceSummary(
            framework="eu-ai-act",
            total_controls=len(results),
            compliant=compliant,
            partial=partial,
            non_compliant=non_c,
            not_applicable=na,
            not_evaluated=ne,
            compliance_rate=rate,
        )
        assert summary.total_controls == len(REQUIREMENTS)


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


def _find(results: list[ControlResult], req_id: str) -> ControlResult:
    for r in results:
        if r.requirement.id == req_id:
            return r
    pytest.fail(f"No result found for {req_id}")
