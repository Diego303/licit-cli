"""Tests for the terminal summary printer."""

from __future__ import annotations

import pytest

from licit.config.schema import LicitConfig
from licit.frameworks.eu_ai_act.evaluator import EUAIActEvaluator
from licit.frameworks.owasp_agentic.evaluator import OWASPAgenticEvaluator
from licit.reports.summary import _progress_bar, print_summary
from licit.reports.unified import UnifiedReport, UnifiedReportGenerator

from tests.conftest import make_context, make_evidence


@pytest.fixture
def report() -> UnifiedReport:
    ctx = make_context()
    ev = make_evidence(has_guardrails=True, guardrail_count=5)
    config = LicitConfig()
    gen = UnifiedReportGenerator(ctx, ev, config)
    return gen.generate([EUAIActEvaluator(), OWASPAgenticEvaluator()])


class TestProgressBar:

    def test_zero_percent(self) -> None:
        bar = _progress_bar(0.0)
        assert bar == "[....................]"

    def test_hundred_percent(self) -> None:
        bar = _progress_bar(100.0)
        assert bar == "[####################]"

    def test_fifty_percent(self) -> None:
        bar = _progress_bar(50.0)
        assert bar == "[##########..........]"

    def test_custom_width(self) -> None:
        bar = _progress_bar(50.0, width=10)
        assert bar == "[#####.....]"

    def test_over_hundred_clamped(self) -> None:
        bar = _progress_bar(150.0)
        assert bar == "[####################]"

    def test_negative_clamped(self) -> None:
        bar = _progress_bar(-10.0)
        assert bar == "[....................]"


class TestPrintSummary:

    def test_prints_project_name(self, report: UnifiedReport, capsys: pytest.CaptureFixture[str]) -> None:
        print_summary(report)
        captured = capsys.readouterr()
        assert "test-project" in captured.out

    def test_prints_framework_names(self, report: UnifiedReport, capsys: pytest.CaptureFixture[str]) -> None:
        print_summary(report)
        captured = capsys.readouterr()
        assert "eu-ai-act" in captured.out
        assert "owasp-agentic" in captured.out

    def test_prints_overall_rate(self, report: UnifiedReport, capsys: pytest.CaptureFixture[str]) -> None:
        print_summary(report)
        captured = capsys.readouterr()
        assert "Overall:" in captured.out
        assert "%" in captured.out

    def test_prints_progress_bar(self, report: UnifiedReport, capsys: pytest.CaptureFixture[str]) -> None:
        print_summary(report)
        captured = capsys.readouterr()
        assert "[" in captured.out
        assert "]" in captured.out

    def test_prints_empty_report(self, capsys: pytest.CaptureFixture[str]) -> None:
        ctx = make_context()
        ev = make_evidence()
        config = LicitConfig()
        gen = UnifiedReportGenerator(ctx, ev, config)
        report = gen.generate([])
        print_summary(report)
        captured = capsys.readouterr()
        assert "Overall:" in captured.out
