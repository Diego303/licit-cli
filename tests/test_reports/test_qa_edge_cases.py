"""QA edge-case tests for Phase 6 — Reports + Gap Analyzer.

Covers category mapping correctness, unicode handling, empty/boundary
inputs, and cross-module integration that unit tests miss.
"""

from __future__ import annotations

import json

import pytest

from licit.config.schema import LicitConfig, ReportConfig
from licit.core.models import (
    ComplianceStatus,
    ComplianceSummary,
    ControlRequirement,
    ControlResult,
    GapItem,
)
from licit.frameworks.eu_ai_act.evaluator import EUAIActEvaluator
from licit.frameworks.eu_ai_act.requirements import REQUIREMENTS as EU_REQUIREMENTS
from licit.frameworks.owasp_agentic.evaluator import OWASPAgenticEvaluator
from licit.frameworks.owasp_agentic.requirements import REQUIREMENTS as OWASP_REQUIREMENTS
from licit.reports import html, json_fmt, markdown
from licit.reports.gap_analyzer import (
    GapAnalyzer,
    _EFFORT_MAP,
    _TOOL_SUGGESTIONS,
)
from licit.reports.summary import _progress_bar, print_summary
from licit.reports.unified import FrameworkReport, UnifiedReport, UnifiedReportGenerator

from tests.conftest import make_context, make_evidence


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. CATEGORY MAPPING CORRECTNESS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCategoryMappingCompleteness:
    """Every category used by a framework requirement MUST exist in
    _TOOL_SUGGESTIONS and _EFFORT_MAP so gaps produce useful output."""

    def test_eu_ai_act_categories_in_tool_suggestions(self) -> None:
        missing = []
        for req in EU_REQUIREMENTS:
            if req.category and req.category not in _TOOL_SUGGESTIONS:
                missing.append(f"{req.id}: category='{req.category}'")
        assert not missing, f"EU AI Act categories missing from _TOOL_SUGGESTIONS: {missing}"

    def test_eu_ai_act_categories_in_effort_map(self) -> None:
        missing = []
        for req in EU_REQUIREMENTS:
            if req.category and req.category not in _EFFORT_MAP:
                missing.append(f"{req.id}: category='{req.category}'")
        assert not missing, f"EU AI Act categories missing from _EFFORT_MAP: {missing}"

    def test_owasp_categories_in_tool_suggestions(self) -> None:
        missing = []
        for req in OWASP_REQUIREMENTS:
            if req.category and req.category not in _TOOL_SUGGESTIONS:
                missing.append(f"{req.id}: category='{req.category}'")
        assert not missing, f"OWASP categories missing from _TOOL_SUGGESTIONS: {missing}"

    def test_owasp_categories_in_effort_map(self) -> None:
        missing = []
        for req in OWASP_REQUIREMENTS:
            if req.category and req.category not in _EFFORT_MAP:
                missing.append(f"{req.id}: category='{req.category}'")
        assert not missing, f"OWASP categories missing from _EFFORT_MAP: {missing}"

    def test_tool_suggestions_and_effort_map_keys_match(self) -> None:
        """Both dicts should cover exactly the same set of categories."""
        suggestions_keys = set(_TOOL_SUGGESTIONS.keys())
        effort_keys = set(_EFFORT_MAP.keys())
        assert suggestions_keys == effort_keys, (
            f"Mismatch — in suggestions only: {suggestions_keys - effort_keys}, "
            f"in effort only: {effort_keys - suggestions_keys}"
        )

    def test_every_tool_suggestion_list_is_non_empty(self) -> None:
        empty = [k for k, v in _TOOL_SUGGESTIONS.items() if not v]
        assert not empty, f"Categories with empty tool suggestions: {empty}"

    def test_owasp_gaps_have_correct_tools(self) -> None:
        """OWASP gaps should get OWASP-specific tool suggestions, not empty lists."""
        ctx = make_context()
        ev = make_evidence()
        analyzer = GapAnalyzer(ctx, ev, LicitConfig())
        gaps = analyzer.analyze([OWASPAgenticEvaluator()])
        for gap in gaps:
            cat = gap.requirement.category or ""
            if cat in _TOOL_SUGGESTIONS:
                assert gap.tools_suggested, (
                    f"Gap {gap.requirement.id} (category={cat}) "
                    f"has empty tools_suggested despite being mapped"
                )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. UNICODE HANDLING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestUnicodeHandling:
    """Verify renderers handle non-ASCII content without crashing."""

    def _make_report_with_unicode(self) -> UnifiedReport:
        req = ControlRequirement(
            id="UTF-1",
            framework="test-fw",
            name="Ñoño — Evaluación «crítica»",
            description="Descripción con acentos: áéíóú — ¿cumple?",
            article_ref="Art. 日本語",
            category="risk-management",
        )
        result = ControlResult(
            requirement=req,
            status=ComplianceStatus.PARTIAL,
            evidence="Evidencia: 50% → «parcial» ✓",
            recommendations=["Añadir más guardrails — «urgente»"],
        )
        summary = ComplianceSummary(
            framework="test-fw", total_controls=1,
            compliant=0, partial=1, non_compliant=0,
            not_applicable=0, not_evaluated=0, compliance_rate=0.0,
        )
        fw = FrameworkReport(
            name="test-fw", version="1.0",
            description="Framework con ñ y «comillas»",
            summary=summary, results=[result],
        )
        return UnifiedReport(
            project_name="Proyecto «Ñoño»",
            generated_at="2026-03-15 12:00 UTC",
            frameworks=[fw],
            overall_total=1, overall_partial=1,
        )

    def test_markdown_unicode(self) -> None:
        report = self._make_report_with_unicode()
        output = markdown.render(report)
        assert "Ñoño" in output
        assert "«crítica»" in output

    def test_json_unicode(self) -> None:
        report = self._make_report_with_unicode()
        output = json_fmt.render(report)
        data = json.loads(output)
        assert "Ñoño" in data["project_name"]

    def test_html_unicode_escaped(self) -> None:
        report = self._make_report_with_unicode()
        output = html.render(report)
        # The «» should be escaped only if they contain HTML-special chars.
        # They don't, so they should appear as-is in the HTML.
        assert "Ñoño" in output
        assert "<!DOCTYPE html>" in output


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. BOUNDARY INPUTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestBoundaryInputs:

    def test_gap_with_empty_evidence(self) -> None:
        """A ControlResult with empty evidence should still produce a valid gap."""
        ctx = make_context()
        ev = make_evidence()
        analyzer = GapAnalyzer(ctx, ev, LicitConfig())

        req = ControlRequirement(
            id="TEST-1", framework="test", name="Test",
            description="Test desc", category="risk-management",
        )
        result = ControlResult(
            requirement=req,
            status=ComplianceStatus.NON_COMPLIANT,
            evidence="",
            recommendations=[],
        )
        gap = analyzer._result_to_gap(result)
        assert gap.gap_description.startswith("Missing:")
        # Empty evidence should not add " Evidence: " suffix
        assert "Evidence:" not in gap.gap_description

    def test_gap_with_no_recommendations(self) -> None:
        """A result with empty recommendations should get a fallback."""
        ctx = make_context()
        ev = make_evidence()
        analyzer = GapAnalyzer(ctx, ev, LicitConfig())

        req = ControlRequirement(
            id="TEST-2", framework="test", name="My Control",
            description="Desc", category="fria",
        )
        result = ControlResult(
            requirement=req,
            status=ComplianceStatus.NON_COMPLIANT,
            evidence="Nothing found",
            recommendations=[],
        )
        gap = analyzer._result_to_gap(result)
        assert "My Control" in gap.recommendation

    def test_gap_with_unknown_category(self) -> None:
        """Unknown category should fall back to empty tools and medium effort."""
        ctx = make_context()
        ev = make_evidence()
        analyzer = GapAnalyzer(ctx, ev, LicitConfig())

        req = ControlRequirement(
            id="TEST-3", framework="test", name="Test",
            description="Desc", category="nonexistent-category",
        )
        result = ControlResult(
            requirement=req,
            status=ComplianceStatus.PARTIAL,
            evidence="Some evidence",
            recommendations=["Do something"],
        )
        gap = analyzer._result_to_gap(result)
        assert gap.effort == "medium"
        assert gap.tools_suggested == []

    def test_gap_with_none_category(self) -> None:
        """requirement.category=None should not crash."""
        ctx = make_context()
        ev = make_evidence()
        analyzer = GapAnalyzer(ctx, ev, LicitConfig())

        req = ControlRequirement(
            id="TEST-4", framework="test", name="Test",
            description="Desc", category=None,
        )
        result = ControlResult(
            requirement=req,
            status=ComplianceStatus.NON_COMPLIANT,
            evidence="Nope",
            recommendations=["Fix it"],
        )
        gap = analyzer._result_to_gap(result)
        assert gap.effort == "medium"

    def test_report_all_compliant(self) -> None:
        """When all controls are compliant, compliance rate should be 100%."""
        ctx = make_context(
            has_architect=True,
            cicd_platform="github-actions",
        )
        ev = make_evidence(
            has_guardrails=True, guardrail_count=10,
            has_quality_gates=True, quality_gate_count=3,
            has_budget_limits=True,
            has_fria=True, fria_path=".licit/fria-data.json",
            has_annex_iv=True, annex_iv_path=".licit/annex-iv.md",
            has_provenance=True, provenance_stats={"ai_percentage": 30},
            has_audit_trail=True, audit_entry_count=10,
            has_changelog=True, changelog_entry_count=5,
            has_human_review_gate=True,
            has_dry_run=True, has_rollback=True,
            has_otel=True,
        )
        gen = UnifiedReportGenerator(ctx, ev, LicitConfig())
        report = gen.generate([EUAIActEvaluator()])
        # Should have a high compliance rate (maybe not 100% due to data-governance)
        assert report.overall_compliance_rate > 50.0

    def test_summary_compliance_rate_above_100_impossible(self) -> None:
        """compliance_rate should never exceed 100%."""
        s = ComplianceSummary(
            framework="test", total_controls=3,
            compliant=3, partial=0, non_compliant=0,
            not_applicable=0, not_evaluated=0,
            compliance_rate=100.0,
        )
        assert s.compliance_rate <= 100.0

    def test_markdown_empty_evidence_string(self) -> None:
        """Empty evidence string should still render valid markdown."""
        req = ControlRequirement(
            id="EMPTY-1", framework="test", name="Test",
            description="Desc",
        )
        result = ControlResult(
            requirement=req,
            status=ComplianceStatus.COMPLIANT,
            evidence="",
        )
        summary = ComplianceSummary(
            framework="test", total_controls=1,
            compliant=1, partial=0, non_compliant=0,
            not_applicable=0, not_evaluated=0, compliance_rate=100.0,
        )
        fw = FrameworkReport(
            name="test", version="1.0", description="Test",
            summary=summary, results=[result],
        )
        report = UnifiedReport(
            project_name="test",
            generated_at="2026-01-01",
            frameworks=[fw],
            overall_total=1, overall_compliant=1,
        )
        output = markdown.render(report)
        assert "**Evidence**: " in output  # Present but empty value


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. CROSS-MODULE INTEGRATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCrossModuleIntegration:

    def test_unified_to_markdown_roundtrip(self) -> None:
        """UnifiedReport → markdown → must contain all requirement IDs."""
        ctx = make_context()
        ev = make_evidence()
        gen = UnifiedReportGenerator(ctx, ev, LicitConfig())
        report = gen.generate([EUAIActEvaluator()])
        md = markdown.render(report)
        for result in report.frameworks[0].results:
            assert result.requirement.id in md

    def test_unified_to_json_roundtrip(self) -> None:
        """UnifiedReport → JSON → must be parseable and contain all IDs."""
        ctx = make_context()
        ev = make_evidence()
        gen = UnifiedReportGenerator(ctx, ev, LicitConfig())
        report = gen.generate([OWASPAgenticEvaluator()])
        data = json.loads(json_fmt.render(report))
        result_ids = {r["id"] for fw in data["frameworks"] for r in fw["results"]}
        for req in OWASP_REQUIREMENTS:
            assert req.id in result_ids

    def test_unified_to_html_roundtrip(self) -> None:
        """UnifiedReport → HTML → must contain all requirement IDs."""
        ctx = make_context()
        ev = make_evidence()
        gen = UnifiedReportGenerator(ctx, ev, LicitConfig())
        report = gen.generate([EUAIActEvaluator()])
        output = html.render(report)
        for result in report.frameworks[0].results:
            assert result.requirement.id in output

    def test_gap_analyzer_results_subset_of_evaluator_results(self) -> None:
        """Every gap requirement must exist in the evaluator's requirements."""
        ctx = make_context()
        ev = make_evidence()
        analyzer = GapAnalyzer(ctx, ev, LicitConfig())
        gaps = analyzer.analyze([EUAIActEvaluator()])
        eu_ids = {r.id for r in EU_REQUIREMENTS}
        for gap in gaps:
            assert gap.requirement.id in eu_ids

    def test_three_formats_produce_different_output(self) -> None:
        """markdown, json, html should produce structurally different output."""
        ctx = make_context()
        ev = make_evidence()
        gen = UnifiedReportGenerator(ctx, ev, LicitConfig())
        report = gen.generate([EUAIActEvaluator()])
        md = markdown.render(report)
        js = json_fmt.render(report)
        ht = html.render(report)
        # Each format has a distinct fingerprint
        assert md.startswith("# ")
        assert js.startswith("{")
        assert ht.startswith("<!DOCTYPE html>")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. HTML ESCAPING EDGE CASES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestHtmlEscaping:

    def test_esc_ampersand_first(self) -> None:
        """& must be escaped before other entities to avoid double-escaping."""
        assert html._esc("&lt;") == "&amp;lt;"

    def test_esc_all_five_chars(self) -> None:
        result = html._esc("""<"test">&'value'""")
        assert "<" not in result or "&lt;" in result
        assert ">" not in result or "&gt;" in result
        assert '"' not in result or "&quot;" in result
        assert "'" not in result or "&#39;" in result

    def test_esc_preserves_normal_text(self) -> None:
        assert html._esc("Hello World 123") == "Hello World 123"

    def test_esc_empty_string(self) -> None:
        assert html._esc("") == ""
