"""Tests for the unified report generator."""

from __future__ import annotations

import pytest

from licit.config.schema import LicitConfig, ReportConfig
from licit.core.models import ComplianceStatus
from licit.frameworks.eu_ai_act.evaluator import EUAIActEvaluator
from licit.frameworks.owasp_agentic.evaluator import OWASPAgenticEvaluator
from licit.reports.unified import FrameworkReport, UnifiedReport, UnifiedReportGenerator

# Re-use helpers from conftest (imported via pytest)
from tests.conftest import make_context, make_evidence


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def generator() -> UnifiedReportGenerator:
    ctx = make_context()
    ev = make_evidence(has_guardrails=True, guardrail_count=5)
    config = LicitConfig()
    return UnifiedReportGenerator(ctx, ev, config)


@pytest.fixture
def full_report(generator: UnifiedReportGenerator) -> UnifiedReport:
    """Generate a report with both frameworks."""
    return generator.generate([EUAIActEvaluator(), OWASPAgenticEvaluator()])


# ── UnifiedReportGenerator tests ─────────────────────────────────


class TestUnifiedReportGenerator:

    def test_generate_with_no_frameworks(self, generator: UnifiedReportGenerator) -> None:
        report = generator.generate([])
        assert report.project_name == "test-project"
        assert report.frameworks == []
        assert report.overall_total == 0
        assert report.overall_compliance_rate == 0.0

    def test_generate_single_framework(self, generator: UnifiedReportGenerator) -> None:
        report = generator.generate([EUAIActEvaluator()])
        assert len(report.frameworks) == 1
        assert report.frameworks[0].name == "eu-ai-act"
        assert report.overall_total > 0

    def test_generate_multiple_frameworks(self, full_report: UnifiedReport) -> None:
        assert len(full_report.frameworks) == 2
        names = {fw.name for fw in full_report.frameworks}
        assert "eu-ai-act" in names
        assert "owasp-agentic" in names

    def test_overall_totals_match_framework_sums(self, full_report: UnifiedReport) -> None:
        expected_total = sum(fw.summary.total_controls for fw in full_report.frameworks)
        assert full_report.overall_total == expected_total

        expected_compliant = sum(fw.summary.compliant for fw in full_report.frameworks)
        assert full_report.overall_compliant == expected_compliant

    def test_compliance_rate_computation(self) -> None:
        ctx = make_context(
            has_architect=True,
            architect_config_path=None,
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
        config = LicitConfig()
        gen = UnifiedReportGenerator(ctx, ev, config)
        report = gen.generate([EUAIActEvaluator()])

        # All these evidence fields should boost compliance
        assert report.overall_compliance_rate > 0

    def test_generated_at_set(self, full_report: UnifiedReport) -> None:
        assert "UTC" in full_report.generated_at

    def test_include_flags_propagated(self) -> None:
        ctx = make_context()
        ev = make_evidence()
        config = LicitConfig(reports=ReportConfig(include_evidence=False,
                                                   include_recommendations=False))
        gen = UnifiedReportGenerator(ctx, ev, config)
        report = gen.generate([EUAIActEvaluator()])
        assert report.include_evidence is False
        assert report.include_recommendations is False


class TestFrameworkReport:

    def test_summary_counts(self, full_report: UnifiedReport) -> None:
        for fw in full_report.frameworks:
            s = fw.summary
            total_counted = (
                s.compliant + s.partial + s.non_compliant
                + s.not_applicable + s.not_evaluated
            )
            assert total_counted == s.total_controls

    def test_results_have_requirements(self, full_report: UnifiedReport) -> None:
        for fw in full_report.frameworks:
            for result in fw.results:
                assert result.requirement.id
                assert result.requirement.name
                assert result.status in ComplianceStatus

    def test_compliance_rate_zero_to_hundred(self, full_report: UnifiedReport) -> None:
        for fw in full_report.frameworks:
            assert 0.0 <= fw.summary.compliance_rate <= 100.0


class TestExceptionHandling:

    def test_failing_framework_skipped(self, generator: UnifiedReportGenerator) -> None:
        """A framework that raises an exception should be skipped, not crash."""

        class BrokenEvaluator:
            name = "broken"
            version = "0.0"
            description = "Always fails"

            def get_requirements(self) -> list:  # type: ignore[type-arg]
                return []

            def evaluate(self, context: object, evidence: object) -> list:  # type: ignore[type-arg]
                msg = "evaluator exploded"
                raise RuntimeError(msg)

        report = generator.generate([BrokenEvaluator(), EUAIActEvaluator()])
        # Broken framework skipped, EU AI Act still present
        assert len(report.frameworks) == 1
        assert report.frameworks[0].name == "eu-ai-act"

    def test_all_frameworks_fail(self, generator: UnifiedReportGenerator) -> None:
        """If all frameworks fail, report should still be valid with zero results."""

        class BrokenEvaluator:
            name = "broken"
            version = "0.0"
            description = "Always fails"

            def get_requirements(self) -> list:  # type: ignore[type-arg]
                return []

            def evaluate(self, context: object, evidence: object) -> list:  # type: ignore[type-arg]
                msg = "boom"
                raise ValueError(msg)

        report = generator.generate([BrokenEvaluator()])
        assert report.frameworks == []
        assert report.overall_total == 0
        assert report.overall_compliance_rate == 0.0
