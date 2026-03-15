"""Tests for the gap analyzer."""

from __future__ import annotations

import pytest

from licit.config.schema import LicitConfig
from licit.core.models import ComplianceStatus, GapItem
from licit.frameworks.eu_ai_act.evaluator import EUAIActEvaluator
from licit.frameworks.owasp_agentic.evaluator import OWASPAgenticEvaluator
from licit.reports.gap_analyzer import GapAnalyzer

from tests.conftest import make_context, make_evidence


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def analyzer_minimal() -> GapAnalyzer:
    """Analyzer with minimal evidence — should produce many gaps."""
    ctx = make_context()
    ev = make_evidence()
    return GapAnalyzer(ctx, ev, LicitConfig())


@pytest.fixture
def analyzer_full() -> GapAnalyzer:
    """Analyzer with extensive evidence — should produce fewer gaps."""
    ctx = make_context(
        has_architect=True,
        cicd_platform="github-actions",
    )
    ev = make_evidence(
        has_guardrails=True,
        guardrail_count=10,
        has_quality_gates=True,
        quality_gate_count=3,
        has_budget_limits=True,
        has_fria=True,
        fria_path=".licit/fria-data.json",
        has_annex_iv=True,
        annex_iv_path=".licit/annex-iv.md",
        has_provenance=True,
        provenance_stats={"ai_percentage": 30},
        has_audit_trail=True,
        audit_entry_count=10,
        has_changelog=True,
        changelog_entry_count=5,
        has_human_review_gate=True,
        has_dry_run=True,
        has_rollback=True,
    )
    return GapAnalyzer(ctx, ev, LicitConfig())


# ── Tests ────────────────────────────────────────────────────────


class TestGapAnalyzer:

    def test_no_frameworks_returns_empty(self, analyzer_minimal: GapAnalyzer) -> None:
        gaps = analyzer_minimal.analyze([])
        assert gaps == []

    def test_minimal_evidence_produces_gaps(self, analyzer_minimal: GapAnalyzer) -> None:
        gaps = analyzer_minimal.analyze([EUAIActEvaluator()])
        assert len(gaps) > 0
        # Without FRIA, should have ART-27-1 gap
        art27_gaps = [g for g in gaps if g.requirement.id == "ART-27-1"]
        assert len(art27_gaps) == 1
        assert art27_gaps[0].status == ComplianceStatus.NON_COMPLIANT

    def test_full_evidence_fewer_gaps(
        self,
        analyzer_minimal: GapAnalyzer,
        analyzer_full: GapAnalyzer,
    ) -> None:
        gaps_min = analyzer_minimal.analyze([EUAIActEvaluator()])
        gaps_full = analyzer_full.analyze([EUAIActEvaluator()])
        assert len(gaps_full) <= len(gaps_min)

    def test_gaps_sorted_by_severity(self, analyzer_minimal: GapAnalyzer) -> None:
        gaps = analyzer_minimal.analyze([EUAIActEvaluator()])
        if len(gaps) < 2:
            pytest.skip("Not enough gaps to test sorting")
        # Non-compliant should appear before partial
        non_compliant_indices = [
            i for i, g in enumerate(gaps)
            if g.status == ComplianceStatus.NON_COMPLIANT
        ]
        partial_indices = [
            i for i, g in enumerate(gaps)
            if g.status == ComplianceStatus.PARTIAL
        ]
        if non_compliant_indices and partial_indices:
            assert max(non_compliant_indices) < min(partial_indices)

    def test_priority_assigned_sequentially(self, analyzer_minimal: GapAnalyzer) -> None:
        gaps = analyzer_minimal.analyze([EUAIActEvaluator()])
        priorities = [g.priority for g in gaps]
        assert priorities == list(range(1, len(gaps) + 1))

    def test_gap_has_recommendation(self, analyzer_minimal: GapAnalyzer) -> None:
        gaps = analyzer_minimal.analyze([EUAIActEvaluator()])
        for gap in gaps:
            assert gap.recommendation
            assert isinstance(gap.recommendation, str)

    def test_gap_has_effort(self, analyzer_minimal: GapAnalyzer) -> None:
        gaps = analyzer_minimal.analyze([EUAIActEvaluator()])
        for gap in gaps:
            assert gap.effort in ("low", "medium", "high")

    def test_gap_description_has_context(self, analyzer_minimal: GapAnalyzer) -> None:
        gaps = analyzer_minimal.analyze([EUAIActEvaluator()])
        for gap in gaps:
            assert gap.gap_description
            # Should start with "Missing" or "Incomplete"
            assert gap.gap_description.startswith(("Missing", "Incomplete"))

    def test_owasp_gaps(self, analyzer_minimal: GapAnalyzer) -> None:
        gaps = analyzer_minimal.analyze([OWASPAgenticEvaluator()])
        # With no evidence, should have some OWASP gaps
        assert len(gaps) > 0
        frameworks = {g.requirement.framework for g in gaps}
        assert "owasp-agentic" in frameworks

    def test_multi_framework_gaps(self, analyzer_minimal: GapAnalyzer) -> None:
        gaps = analyzer_minimal.analyze([EUAIActEvaluator(), OWASPAgenticEvaluator()])
        frameworks = {g.requirement.framework for g in gaps}
        assert "eu-ai-act" in frameworks
        assert "owasp-agentic" in frameworks

    def test_compliant_not_in_gaps(self, analyzer_full: GapAnalyzer) -> None:
        gaps = analyzer_full.analyze([EUAIActEvaluator()])
        statuses = {g.status for g in gaps}
        assert ComplianceStatus.COMPLIANT not in statuses
        assert ComplianceStatus.NOT_APPLICABLE not in statuses
        assert ComplianceStatus.NOT_EVALUATED not in statuses

    def test_failing_framework_skipped(self, analyzer_minimal: GapAnalyzer) -> None:
        """A framework that raises should be skipped, not crash gap analysis."""

        class BrokenEvaluator:
            name = "broken"
            version = "0.0"
            description = "Fails"

            def get_requirements(self) -> list:  # type: ignore[type-arg]
                return []

            def evaluate(self, context: object, evidence: object) -> list:  # type: ignore[type-arg]
                msg = "evaluator error"
                raise RuntimeError(msg)

        gaps = analyzer_minimal.analyze([BrokenEvaluator(), EUAIActEvaluator()])
        # EU AI Act gaps should still be present
        frameworks = {g.requirement.framework for g in gaps}
        assert "eu-ai-act" in frameworks

    def test_all_frameworks_fail_returns_empty(self, analyzer_minimal: GapAnalyzer) -> None:
        """If all frameworks fail, should return empty list, not crash."""

        class BrokenEvaluator:
            name = "broken"
            version = "0.0"
            description = "Fails"

            def get_requirements(self) -> list:  # type: ignore[type-arg]
                return []

            def evaluate(self, context: object, evidence: object) -> list:  # type: ignore[type-arg]
                msg = "boom"
                raise ValueError(msg)

        gaps = analyzer_minimal.analyze([BrokenEvaluator()])
        assert gaps == []

    def test_data_governance_has_tool_suggestions(self, analyzer_minimal: GapAnalyzer) -> None:
        """Ensure data-governance category has tool suggestions (not empty)."""
        from licit.reports.gap_analyzer import _TOOL_SUGGESTIONS

        assert len(_TOOL_SUGGESTIONS["data-governance"]) > 0
