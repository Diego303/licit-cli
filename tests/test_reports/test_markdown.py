"""Tests for the Markdown report renderer."""

from __future__ import annotations

import pytest

from licit.config.schema import LicitConfig, ReportConfig
from licit.frameworks.eu_ai_act.evaluator import EUAIActEvaluator
from licit.frameworks.owasp_agentic.evaluator import OWASPAgenticEvaluator
from licit.reports import markdown
from licit.reports.unified import UnifiedReport, UnifiedReportGenerator

from tests.conftest import make_context, make_evidence


@pytest.fixture
def report() -> UnifiedReport:
    ctx = make_context()
    ev = make_evidence(has_guardrails=True, guardrail_count=5)
    config = LicitConfig()
    gen = UnifiedReportGenerator(ctx, ev, config)
    return gen.generate([EUAIActEvaluator(), OWASPAgenticEvaluator()])


class TestMarkdownRenderer:

    def test_render_contains_project_name(self, report: UnifiedReport) -> None:
        output = markdown.render(report)
        assert "test-project" in output

    def test_render_has_framework_sections(self, report: UnifiedReport) -> None:
        output = markdown.render(report)
        assert "## eu-ai-act" in output
        assert "## owasp-agentic" in output

    def test_render_has_overall_summary(self, report: UnifiedReport) -> None:
        output = markdown.render(report)
        assert "## Overall Summary" in output
        assert "Compliance rate" in output

    def test_render_has_status_icons(self, report: UnifiedReport) -> None:
        output = markdown.render(report)
        # At least one of these should appear
        assert any(tag in output for tag in ["[PASS]", "[FAIL]", "[PARTIAL]", "[?]"])

    def test_render_has_evidence(self, report: UnifiedReport) -> None:
        output = markdown.render(report)
        assert "**Evidence**" in output

    def test_render_without_evidence(self) -> None:
        ctx = make_context()
        ev = make_evidence()
        config = LicitConfig(reports=ReportConfig(include_evidence=False))
        gen = UnifiedReportGenerator(ctx, ev, config)
        report = gen.generate([EUAIActEvaluator()])
        output = markdown.render(report)
        assert "**Evidence**" not in output

    def test_render_without_recommendations(self) -> None:
        ctx = make_context()
        ev = make_evidence()
        config = LicitConfig(reports=ReportConfig(include_recommendations=False))
        gen = UnifiedReportGenerator(ctx, ev, config)
        report = gen.generate([EUAIActEvaluator()])
        output = markdown.render(report)
        assert "**Recommendations:**" not in output

    def test_render_has_footer(self, report: UnifiedReport) -> None:
        output = markdown.render(report)
        assert "licit" in output
        assert "---" in output

    def test_render_empty_frameworks(self) -> None:
        ctx = make_context()
        ev = make_evidence()
        config = LicitConfig()
        gen = UnifiedReportGenerator(ctx, ev, config)
        report = gen.generate([])
        output = markdown.render(report)
        assert "## Overall Summary" in output
        assert "0" in output

    def test_render_valid_markdown_table(self, report: UnifiedReport) -> None:
        output = markdown.render(report)
        # Check for valid table separators
        assert "|--------|-------|" in output
