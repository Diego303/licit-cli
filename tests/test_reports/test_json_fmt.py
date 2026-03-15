"""Tests for the JSON report renderer."""

from __future__ import annotations

import json

import pytest

from licit.config.schema import LicitConfig, ReportConfig
from licit.frameworks.eu_ai_act.evaluator import EUAIActEvaluator
from licit.frameworks.owasp_agentic.evaluator import OWASPAgenticEvaluator
from licit.reports import json_fmt
from licit.reports.unified import UnifiedReport, UnifiedReportGenerator

from tests.conftest import make_context, make_evidence


@pytest.fixture
def report() -> UnifiedReport:
    ctx = make_context()
    ev = make_evidence(has_guardrails=True, guardrail_count=5)
    config = LicitConfig()
    gen = UnifiedReportGenerator(ctx, ev, config)
    return gen.generate([EUAIActEvaluator(), OWASPAgenticEvaluator()])


class TestJsonRenderer:

    def test_render_valid_json(self, report: UnifiedReport) -> None:
        output = json_fmt.render(report)
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_render_has_project_name(self, report: UnifiedReport) -> None:
        data = json.loads(json_fmt.render(report))
        assert data["project_name"] == "test-project"

    def test_render_has_overall_section(self, report: UnifiedReport) -> None:
        data = json.loads(json_fmt.render(report))
        overall = data["overall"]
        assert "total_controls" in overall
        assert "compliant" in overall
        assert "compliance_rate" in overall

    def test_render_has_frameworks(self, report: UnifiedReport) -> None:
        data = json.loads(json_fmt.render(report))
        assert len(data["frameworks"]) == 2
        names = {fw["name"] for fw in data["frameworks"]}
        assert "eu-ai-act" in names
        assert "owasp-agentic" in names

    def test_render_results_have_fields(self, report: UnifiedReport) -> None:
        data = json.loads(json_fmt.render(report))
        for fw in data["frameworks"]:
            for result in fw["results"]:
                assert "id" in result
                assert "name" in result
                assert "status" in result
                assert "evidence" in result
                assert "recommendations" in result

    def test_render_without_evidence(self) -> None:
        ctx = make_context()
        ev = make_evidence()
        config = LicitConfig(reports=ReportConfig(include_evidence=False))
        gen = UnifiedReportGenerator(ctx, ev, config)
        report = gen.generate([EUAIActEvaluator()])
        data = json.loads(json_fmt.render(report))
        for fw in data["frameworks"]:
            for result in fw["results"]:
                assert "evidence" not in result

    def test_render_without_recommendations(self) -> None:
        ctx = make_context()
        ev = make_evidence()
        config = LicitConfig(reports=ReportConfig(include_recommendations=False))
        gen = UnifiedReportGenerator(ctx, ev, config)
        report = gen.generate([EUAIActEvaluator()])
        data = json.loads(json_fmt.render(report))
        for fw in data["frameworks"]:
            for result in fw["results"]:
                assert "recommendations" not in result

    def test_render_summary_counts(self, report: UnifiedReport) -> None:
        data = json.loads(json_fmt.render(report))
        for fw in data["frameworks"]:
            s = fw["summary"]
            total = (
                s["compliant"] + s["partial"] + s["non_compliant"]
                + s["not_applicable"] + s["not_evaluated"]
            )
            assert total == s["total_controls"]

    def test_render_empty_frameworks(self) -> None:
        ctx = make_context()
        ev = make_evidence()
        config = LicitConfig()
        gen = UnifiedReportGenerator(ctx, ev, config)
        report = gen.generate([])
        data = json.loads(json_fmt.render(report))
        assert data["frameworks"] == []
        assert data["overall"]["total_controls"] == 0

    def test_render_generated_at(self, report: UnifiedReport) -> None:
        data = json.loads(json_fmt.render(report))
        assert "generated_at" in data
        assert "UTC" in data["generated_at"]
