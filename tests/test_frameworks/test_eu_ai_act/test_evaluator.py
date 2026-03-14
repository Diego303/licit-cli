"""Tests for the EU AI Act evaluator."""

from __future__ import annotations

import pytest

from licit.core.models import ComplianceStatus, ControlResult
from licit.core.project import AgentConfigFile, SecurityTooling
from licit.frameworks.eu_ai_act.evaluator import EUAIActEvaluator
from licit.frameworks.eu_ai_act.requirements import REQUIREMENTS
from tests.conftest import make_context, make_evidence


@pytest.fixture
def evaluator() -> EUAIActEvaluator:
    return EUAIActEvaluator()


# ── Properties ─────────────────────────────────────────────────────


class TestEvaluatorProperties:
    def test_name(self, evaluator: EUAIActEvaluator) -> None:
        assert evaluator.name == "eu-ai-act"

    def test_version(self, evaluator: EUAIActEvaluator) -> None:
        assert evaluator.version == "2024/1689"

    def test_description(self, evaluator: EUAIActEvaluator) -> None:
        assert "European Union" in evaluator.description

    def test_get_requirements_returns_all(self, evaluator: EUAIActEvaluator) -> None:
        reqs = evaluator.get_requirements()
        assert len(reqs) == len(REQUIREMENTS)
        ids = {r.id for r in reqs}
        assert "ART-9-1" in ids
        assert "ART-27-1" in ids
        assert "ANNEX-IV" in ids


# ── Full evaluation ────────────────────────────────────────────────


class TestEvaluateAll:
    def test_all_requirements_are_evaluated(self, evaluator: EUAIActEvaluator) -> None:
        """Every requirement should produce a result."""
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        assert len(results) == len(REQUIREMENTS)
        req_ids = {r.requirement.id for r in results}
        for req in REQUIREMENTS:
            assert req.id in req_ids

    def test_results_have_valid_status(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        valid = set(ComplianceStatus)
        for r in results:
            assert r.status in valid

    def test_results_have_evidence(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        for r in results:
            assert r.evidence, f"Result for {r.requirement.id} has empty evidence"


# ── Article 9: Risk Management ─────────────────────────────────────


class TestArt9:
    def test_compliant_with_full_risk_management(
        self, evaluator: EUAIActEvaluator
    ) -> None:
        ctx = make_context(security=SecurityTooling(has_vigil=True))
        ev = make_evidence(
            has_guardrails=True,
            guardrail_count=10,
            has_quality_gates=True,
            quality_gate_count=3,
            has_budget_limits=True,
        )
        results = evaluator.evaluate(ctx, ev)
        art9 = _find_result(results, "ART-9-1")
        assert art9.status == ComplianceStatus.COMPLIANT
        assert "Guardrails" in art9.evidence
        assert not art9.recommendations

    def test_partial_with_guardrails_only(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence(has_guardrails=True, guardrail_count=5)
        results = evaluator.evaluate(ctx, ev)
        art9 = _find_result(results, "ART-9-1")
        assert art9.status == ComplianceStatus.PARTIAL

    def test_non_compliant_with_nothing(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        art9 = _find_result(results, "ART-9-1")
        assert art9.status == ComplianceStatus.NON_COMPLIANT
        assert art9.recommendations

    def test_security_scanning_contributes(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context(
            security=SecurityTooling(has_vigil=True, has_semgrep=True)
        )
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        art9 = _find_result(results, "ART-9-1")
        assert art9.status == ComplianceStatus.PARTIAL
        assert "vigil" in art9.evidence
        assert "semgrep" in art9.evidence


# ── Article 10: Data Governance ────────────────────────────────────


class TestArt10:
    def test_always_partial_for_deployer(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        art10 = _find_result(results, "ART-10-1")
        assert art10.status == ComplianceStatus.PARTIAL
        assert "Model provider" in art10.evidence


# ── Article 12: Record Keeping ─────────────────────────────────────


class TestArt12:
    def test_compliant_with_git_audit_provenance(
        self, evaluator: EUAIActEvaluator
    ) -> None:
        ctx = make_context(git_initialized=True, total_commits=100)
        ev = make_evidence(
            has_audit_trail=True,
            audit_entry_count=50,
            has_provenance=True,
            provenance_stats={"ai_percentage": 30.0},
        )
        results = evaluator.evaluate(ctx, ev)
        art12 = _find_result(results, "ART-12-1")
        assert art12.status == ComplianceStatus.COMPLIANT
        assert "Git history" in art12.evidence
        assert "audit trail" in art12.evidence.lower()

    def test_partial_with_git_only(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context(git_initialized=True, total_commits=50)
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        art12 = _find_result(results, "ART-12-1")
        assert art12.status == ComplianceStatus.PARTIAL

    def test_non_compliant_without_git(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context(git_initialized=False, total_commits=0)
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        art12 = _find_result(results, "ART-12-1")
        assert art12.status == ComplianceStatus.NON_COMPLIANT

    def test_provenance_stats_display(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence(
            has_provenance=True,
            provenance_stats={"ai_percentage": 42.5},
        )
        results = evaluator.evaluate(ctx, ev)
        art12 = _find_result(results, "ART-12-1")
        assert "42%" in art12.evidence or "43%" in art12.evidence


# ── Article 13: Transparency ──────────────────────────────────────


class TestArt13:
    def test_compliant_with_annex_iv(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence(has_annex_iv=True)
        results = evaluator.evaluate(ctx, ev)
        art13 = _find_result(results, "ART-13-1")
        assert art13.status == ComplianceStatus.COMPLIANT

    def test_partial_with_changelog_only(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence(has_changelog=True, changelog_entry_count=5)
        results = evaluator.evaluate(ctx, ev)
        art13 = _find_result(results, "ART-13-1")
        assert art13.status == ComplianceStatus.PARTIAL

    def test_non_compliant_with_nothing(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        art13 = _find_result(results, "ART-13-1")
        assert art13.status == ComplianceStatus.NON_COMPLIANT
        assert any("annex-iv" in r.lower() for r in art13.recommendations)


# ── Article 14: Human Oversight ────────────────────────────────────


class TestArt14:
    def test_compliant_with_full_oversight(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence(
            has_dry_run=True,
            has_human_review_gate=True,
            has_quality_gates=True,
            has_budget_limits=True,
        )
        results = evaluator.evaluate(ctx, ev)
        art14 = _find_result(results, "ART-14-1")
        assert art14.status == ComplianceStatus.COMPLIANT

    def test_partial_with_human_review_only(
        self, evaluator: EUAIActEvaluator
    ) -> None:
        ctx = make_context()
        ev = make_evidence(has_human_review_gate=True)
        results = evaluator.evaluate(ctx, ev)
        art14 = _find_result(results, "ART-14-1")
        assert art14.status == ComplianceStatus.PARTIAL

    def test_non_compliant_with_nothing(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        art14 = _find_result(results, "ART-14-1")
        assert art14.status == ComplianceStatus.NON_COMPLIANT

    def test_14_4a_delegates_to_14_1(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence(has_human_review_gate=True, has_dry_run=True)
        results = evaluator.evaluate(ctx, ev)
        art14_1 = _find_result(results, "ART-14-1")
        art14_4a = _find_result(results, "ART-14-4a")
        assert art14_4a.status == art14_1.status

    def test_14_4d_compliant_with_rollback(
        self, evaluator: EUAIActEvaluator
    ) -> None:
        ctx = make_context()
        ev = make_evidence(has_dry_run=True, has_rollback=True)
        results = evaluator.evaluate(ctx, ev)
        art14_4d = _find_result(results, "ART-14-4d")
        assert art14_4d.status == ComplianceStatus.COMPLIANT

    def test_14_4d_partial_without_rollback(
        self, evaluator: EUAIActEvaluator
    ) -> None:
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        art14_4d = _find_result(results, "ART-14-4d")
        assert art14_4d.status == ComplianceStatus.PARTIAL


# ── Article 26: Deployer Obligations ───────────────────────────────


class TestArt26:
    def test_26_1_compliant_with_configs(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context(
            agent_configs=[AgentConfigFile(path="CLAUDE.md", agent_type="claude-code")]
        )
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        art26 = _find_result(results, "ART-26-1")
        assert art26.status == ComplianceStatus.COMPLIANT
        assert "1 agent configs" in art26.evidence

    def test_26_1_partial_without_configs(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context(agent_configs=[])
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        art26 = _find_result(results, "ART-26-1")
        assert art26.status == ComplianceStatus.PARTIAL

    def test_26_5_delegates_to_12_1(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context(git_initialized=True, total_commits=100)
        ev = make_evidence(has_audit_trail=True, audit_entry_count=10, has_provenance=True)
        results = evaluator.evaluate(ctx, ev)
        art26_5 = _find_result(results, "ART-26-5")
        art12 = _find_result(results, "ART-12-1")
        assert art26_5.status == art12.status


# ── Article 27: FRIA ───────────────────────────────────────────────


class TestArt27:
    def test_non_compliant_without_fria(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence(has_fria=False)
        results = evaluator.evaluate(ctx, ev)
        art27 = _find_result(results, "ART-27-1")
        assert art27.status == ComplianceStatus.NON_COMPLIANT
        assert any("licit fria" in r for r in art27.recommendations)

    def test_compliant_with_fria(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence(has_fria=True, fria_path=".licit/fria-data.json")
        results = evaluator.evaluate(ctx, ev)
        art27 = _find_result(results, "ART-27-1")
        assert art27.status == ComplianceStatus.COMPLIANT
        assert "fria-data.json" in art27.evidence


# ── Annex IV ───────────────────────────────────────────────────────


class TestAnnexIV:
    def test_non_compliant_without_docs(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence(has_annex_iv=False)
        results = evaluator.evaluate(ctx, ev)
        annex = _find_result(results, "ANNEX-IV")
        assert annex.status == ComplianceStatus.NON_COMPLIANT
        assert any("annex-iv" in r.lower() for r in annex.recommendations)

    def test_compliant_with_docs(self, evaluator: EUAIActEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence(has_annex_iv=True, annex_iv_path=".licit/annex-iv.md")
        results = evaluator.evaluate(ctx, ev)
        annex = _find_result(results, "ANNEX-IV")
        assert annex.status == ComplianceStatus.COMPLIANT


# ── Helpers ────────────────────────────────────────────────────────


def _find_result(
    results: list[ControlResult],
    req_id: str,
) -> ControlResult:
    """Find a ControlResult by requirement ID."""
    for r in results:
        if r.requirement.id == req_id:
            return r
    pytest.fail(f"No result found for requirement {req_id}")
