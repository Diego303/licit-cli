"""Tests for the HTML report renderer."""

from __future__ import annotations

import pytest

from licit.config.schema import LicitConfig, ReportConfig
from licit.frameworks.eu_ai_act.evaluator import EUAIActEvaluator
from licit.frameworks.owasp_agentic.evaluator import OWASPAgenticEvaluator
from licit.reports import html
from licit.reports.unified import UnifiedReport, UnifiedReportGenerator

from tests.conftest import make_context, make_evidence


@pytest.fixture
def report() -> UnifiedReport:
    ctx = make_context()
    ev = make_evidence(has_guardrails=True, guardrail_count=5)
    config = LicitConfig()
    gen = UnifiedReportGenerator(ctx, ev, config)
    return gen.generate([EUAIActEvaluator(), OWASPAgenticEvaluator()])


class TestHtmlRenderer:

    def test_render_valid_html(self, report: UnifiedReport) -> None:
        output = html.render(report)
        assert output.startswith("<!DOCTYPE html>")
        assert "</html>" in output

    def test_render_has_project_name(self, report: UnifiedReport) -> None:
        output = html.render(report)
        assert "test-project" in output

    def test_render_has_framework_sections(self, report: UnifiedReport) -> None:
        output = html.render(report)
        assert "eu-ai-act" in output
        assert "owasp-agentic" in output

    def test_render_has_style_tag(self, report: UnifiedReport) -> None:
        output = html.render(report)
        assert "<style>" in output
        assert "</style>" in output

    def test_render_has_status_badges(self, report: UnifiedReport) -> None:
        output = html.render(report)
        assert 'class="badge"' in output

    def test_render_escapes_html(self) -> None:
        """Ensure special characters are escaped."""
        output = html._esc('<script>alert("xss")</script>')
        assert "<" not in output
        assert "&lt;" in output
        assert "&gt;" in output
        assert "&quot;" in output

    def test_render_escapes_single_quotes(self) -> None:
        """Ensure single quotes are escaped for attribute safety."""
        output = html._esc("it's a test")
        assert "'" not in output
        assert "&#39;" in output

    def test_render_without_evidence(self) -> None:
        ctx = make_context()
        ev = make_evidence()
        config = LicitConfig(reports=ReportConfig(include_evidence=False))
        gen = UnifiedReportGenerator(ctx, ev, config)
        report = gen.generate([EUAIActEvaluator()])
        output = html.render(report)
        assert 'class="evidence"' not in output

    def test_render_without_recommendations(self) -> None:
        ctx = make_context()
        ev = make_evidence()
        config = LicitConfig(reports=ReportConfig(include_recommendations=False))
        gen = UnifiedReportGenerator(ctx, ev, config)
        report = gen.generate([EUAIActEvaluator()])
        output = html.render(report)
        assert 'class="rec"' not in output

    def test_render_has_footer(self, report: UnifiedReport) -> None:
        output = html.render(report)
        assert "<footer>" in output
        assert "licit" in output

    def test_render_single_file_no_deps(self, report: UnifiedReport) -> None:
        """HTML should be self-contained — no external links."""
        output = html.render(report)
        # No external CSS/JS references
        assert 'rel="stylesheet"' not in output
        assert "<script src=" not in output

    def test_render_empty_frameworks(self) -> None:
        ctx = make_context()
        ev = make_evidence()
        config = LicitConfig()
        gen = UnifiedReportGenerator(ctx, ev, config)
        report = gen.generate([])
        output = html.render(report)
        assert "<!DOCTYPE html>" in output
        assert "Overall Summary" in output
