"""QA edge-case and regression tests for Phase 5 — OWASP Agentic Top 10.

Covers: Protocol conformance, _score_to_status boundaries, provenance
stats edge cases, _safe_float robustness, registry interop, CLI integration,
requirements integrity, cross-module compatibility, and OTel bonus scoring.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from licit.core.models import ComplianceStatus, ControlResult
from licit.core.project import AgentConfigFile, SecurityTooling
from licit.frameworks.base import ComplianceFramework
from licit.frameworks.owasp_agentic.evaluator import (
    OWASPAgenticEvaluator,
    _safe_float,
    _score_to_status,
)
from licit.frameworks.owasp_agentic.requirements import REQUIREMENTS
from licit.frameworks.registry import FrameworkRegistry
from tests.conftest import make_context, make_evidence

# ═══════════════════════════════════════════════════════════════════
# 1. Protocol conformance
# ═══════════════════════════════════════════════════════════════════


class TestProtocolConformance:
    """Verify OWASPAgenticEvaluator satisfies the ComplianceFramework Protocol."""

    def test_isinstance_check(self) -> None:
        evaluator = OWASPAgenticEvaluator()
        assert isinstance(evaluator, ComplianceFramework)

    def test_evaluate_signature_matches_protocol(self) -> None:
        evaluator = OWASPAgenticEvaluator()
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, ControlResult)

    def test_get_requirements_returns_control_requirements(self) -> None:
        from licit.core.models import ControlRequirement

        evaluator = OWASPAgenticEvaluator()
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
        assert _score_to_status(1, compliant_at=2, partial_at=2) == ComplianceStatus.NON_COMPLIANT
        assert _score_to_status(2, compliant_at=2, partial_at=2) == ComplianceStatus.COMPLIANT

    def test_asi08_thresholds(self) -> None:
        """ASI08 uses compliant_at=2, partial_at=1 — verify that works."""
        assert _score_to_status(0, compliant_at=2, partial_at=1) == ComplianceStatus.NON_COMPLIANT
        assert _score_to_status(1, compliant_at=2, partial_at=1) == ComplianceStatus.PARTIAL
        assert _score_to_status(2, compliant_at=2, partial_at=1) == ComplianceStatus.COMPLIANT


# ═══════════════════════════════════════════════════════════════════
# 3. _safe_float robustness
# ═══════════════════════════════════════════════════════════════════


class TestSafeFloat:
    def test_int_value(self) -> None:
        assert _safe_float(42) == 42.0

    def test_float_value(self) -> None:
        assert _safe_float(3.14) == 3.14

    def test_zero(self) -> None:
        assert _safe_float(0) == 0.0

    def test_string_returns_zero(self) -> None:
        assert _safe_float("not-a-number") == 0.0

    def test_none_returns_zero(self) -> None:
        assert _safe_float(None) == 0.0

    def test_list_returns_zero(self) -> None:
        assert _safe_float([1, 2, 3]) == 0.0

    def test_bool_true(self) -> None:
        # bool is subclass of int in Python
        assert _safe_float(True) == 1.0

    def test_negative_float(self) -> None:
        assert _safe_float(-5.5) == -5.5


# ═══════════════════════════════════════════════════════════════════
# 4. Evaluator edge cases
# ═══════════════════════════════════════════════════════════════════


class TestEvaluatorEdgeCases:
    def test_provenance_stats_with_string_percentage(self) -> None:
        """Non-numeric ai_percentage should fallback to 0 gracefully."""
        evaluator = OWASPAgenticEvaluator()
        ctx = make_context(git_initialized=True)
        ev = make_evidence(
            has_provenance=True,
            provenance_stats={"ai_percentage": "invalid"},
        )
        results = evaluator.evaluate(ctx, ev)
        asi04 = _find(results, "ASI04")
        assert "0%" in asi04.evidence

    def test_provenance_stats_with_none_percentage(self) -> None:
        evaluator = OWASPAgenticEvaluator()
        ctx = make_context()
        ev = make_evidence(
            has_provenance=True,
            provenance_stats={"ai_percentage": None},
        )
        results = evaluator.evaluate(ctx, ev)
        asi04 = _find(results, "ASI04")
        assert "0%" in asi04.evidence

    def test_provenance_stats_missing_key(self) -> None:
        evaluator = OWASPAgenticEvaluator()
        ctx = make_context()
        ev = make_evidence(has_provenance=True, provenance_stats={})
        results = evaluator.evaluate(ctx, ev)
        asi04 = _find(results, "ASI04")
        assert "0%" in asi04.evidence

    def test_otel_bonus_scoring_in_asi04(self) -> None:
        """OTel should contribute +1 to ASI04 logging score."""
        evaluator = OWASPAgenticEvaluator()
        ctx = make_context(git_initialized=True, total_commits=50)
        ev_without_otel = make_evidence(
            has_audit_trail=True, audit_entry_count=10,
        )
        ev_with_otel = make_evidence(
            has_audit_trail=True, audit_entry_count=10,
            has_otel=True,
        )
        r_without = evaluator.evaluate(ctx, ev_without_otel)
        r_with = evaluator.evaluate(ctx, ev_with_otel)
        asi04_without = _find(r_without, "ASI04")
        asi04_with = _find(r_with, "ASI04")
        # OTel pushes from COMPLIANT(3) to COMPLIANT(4), or improves evidence
        assert "OpenTelemetry" in asi04_with.evidence
        assert "OpenTelemetry" not in asi04_without.evidence

    def test_multiple_sca_tools_listed(self) -> None:
        """ASI03 should list all detected SCA tools."""
        evaluator = OWASPAgenticEvaluator()
        ctx = make_context(
            security=SecurityTooling(
                has_snyk=True, has_semgrep=True, has_codeql=True, has_trivy=True,
            ),
        )
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi03 = _find(results, "ASI03")
        assert "Snyk" in asi03.evidence
        assert "Semgrep" in asi03.evidence
        assert "CodeQL" in asi03.evidence
        assert "Trivy" in asi03.evidence

    def test_cicd_platform_displayed_in_evidence(self) -> None:
        """ASI07 and ASI09 should show the detected CI/CD platform name."""
        evaluator = OWASPAgenticEvaluator()
        ctx = make_context(cicd_platform="gitlab-ci")
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi07 = _find(results, "ASI07")
        assert "gitlab-ci" in asi07.evidence
        asi09 = _find(results, "ASI09")
        assert "gitlab-ci" in asi09.evidence

    def test_test_framework_displayed_in_evidence(self) -> None:
        """ASI05 and ASI09 should show test framework name."""
        evaluator = OWASPAgenticEvaluator()
        ctx = make_context()
        ctx.test_framework = "jest"
        ctx.test_dirs = ["__tests__"]
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi05 = _find(results, "ASI05")
        assert "jest" in asi05.evidence
        asi09 = _find(results, "ASI09")
        assert "jest" in asi09.evidence

    def test_recommendations_are_actionable_strings(self) -> None:
        """All recommendations should be non-empty strings."""
        evaluator = OWASPAgenticEvaluator()
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        for r in results:
            for rec in r.recommendations:
                assert isinstance(rec, str)
                assert len(rec) > 5, f"Recommendation too short: {rec!r}"

    def test_all_compliant_scenario(self) -> None:
        """A fully-equipped project should have all 10 requirements compliant."""
        evaluator = OWASPAgenticEvaluator()
        ctx = make_context(
            agent_configs=[AgentConfigFile(path="CLAUDE.md", agent_type="claude-code")],
            cicd_platform="github-actions",
            git_initialized=True,
            total_commits=200,
            security=SecurityTooling(
                has_vigil=True, has_semgrep=True, has_snyk=True,
            ),
        )
        ctx.test_framework = "pytest"
        ctx.test_dirs = ["tests"]
        ev = make_evidence(
            has_guardrails=True, guardrail_count=20,
            has_quality_gates=True, quality_gate_count=5,
            has_budget_limits=True,
            has_human_review_gate=True,
            has_dry_run=True,
            has_rollback=True,
            has_audit_trail=True, audit_entry_count=100,
            has_provenance=True, provenance_stats={"ai_percentage": 35.0},
            has_changelog=True, changelog_entry_count=10,
            has_otel=True,
        )
        results = evaluator.evaluate(ctx, ev)
        for r in results:
            assert r.status == ComplianceStatus.COMPLIANT, (
                f"{r.requirement.id} ({r.requirement.name}) is {r.status}, "
                f"expected COMPLIANT. Evidence: {r.evidence}"
            )

    def test_all_non_compliant_scenario(self) -> None:
        """A bare project with absolutely nothing should be all non-compliant."""
        evaluator = OWASPAgenticEvaluator()
        ctx = make_context(
            agent_configs=[],
            cicd_platform="none",
            git_initialized=False,
            total_commits=0,
        )
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        non_compliant = [r for r in results if r.status == ComplianceStatus.NON_COMPLIANT]
        assert len(non_compliant) == 10

    def test_idempotent_evaluation(self) -> None:
        """Calling evaluate() twice with same inputs gives identical results."""
        evaluator = OWASPAgenticEvaluator()
        ctx = make_context(
            agent_configs=[AgentConfigFile(path="CLAUDE.md", agent_type="claude-code")],
            security=SecurityTooling(has_vigil=True),
        )
        ev = make_evidence(has_guardrails=True, guardrail_count=5, has_budget_limits=True)
        results1 = evaluator.evaluate(ctx, ev)
        results2 = evaluator.evaluate(ctx, ev)
        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert r1.requirement.id == r2.requirement.id
            assert r1.status == r2.status
            assert r1.evidence == r2.evidence
            assert r1.recommendations == r2.recommendations

    def test_compliant_results_have_empty_recommendations(self) -> None:
        """Compliant controls should not carry recommendations."""
        evaluator = OWASPAgenticEvaluator()
        ctx = make_context(
            agent_configs=[AgentConfigFile(path="CLAUDE.md", agent_type="claude-code")],
            cicd_platform="github-actions",
            git_initialized=True,
            total_commits=200,
            security=SecurityTooling(has_vigil=True, has_semgrep=True, has_snyk=True),
        )
        ctx.test_framework = "pytest"
        ctx.test_dirs = ["tests"]
        ev = make_evidence(
            has_guardrails=True, guardrail_count=20,
            has_quality_gates=True, quality_gate_count=5,
            has_budget_limits=True,
            has_human_review_gate=True,
            has_dry_run=True,
            has_rollback=True,
            has_audit_trail=True, audit_entry_count=100,
            has_provenance=True, provenance_stats={"ai_percentage": 35.0},
            has_changelog=True, changelog_entry_count=10,
            has_otel=True,
        )
        results = evaluator.evaluate(ctx, ev)
        for r in results:
            if r.status == ComplianceStatus.COMPLIANT:
                assert r.recommendations == [], (
                    f"{r.requirement.id} is COMPLIANT but has recommendations: "
                    f"{r.recommendations}"
                )

    def test_non_compliant_results_always_have_recommendations(self) -> None:
        """Non-compliant controls must include at least one recommendation."""
        evaluator = OWASPAgenticEvaluator()
        ctx = make_context(
            agent_configs=[], cicd_platform="none",
            git_initialized=False, total_commits=0,
        )
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        for r in results:
            if r.status == ComplianceStatus.NON_COMPLIANT:
                assert len(r.recommendations) >= 1, (
                    f"{r.requirement.id} is NON_COMPLIANT but has no recommendations"
                )

    def test_security_findings_do_not_affect_scoring(self) -> None:
        """security_findings_* fields should not change any OWASP scores.

        The evaluator checks for tool presence, not their findings.
        This ensures that a project with 0 findings gets the same
        score as one with 100 critical findings (given same tools).
        """
        evaluator = OWASPAgenticEvaluator()
        ctx = make_context(security=SecurityTooling(has_vigil=True))
        ev_clean = make_evidence(has_guardrails=True)
        ev_dirty = make_evidence(
            has_guardrails=True,
            security_findings_total=100,
            security_findings_critical=50,
            security_findings_high=30,
        )
        r_clean = evaluator.evaluate(ctx, ev_clean)
        r_dirty = evaluator.evaluate(ctx, ev_dirty)
        for rc, rd in zip(r_clean, r_dirty):
            assert rc.status == rd.status, (
                f"{rc.requirement.id}: clean={rc.status}, dirty={rd.status}"
            )

    def test_guardrail_count_zero_evidence_message(self) -> None:
        """has_guardrails=True with guardrail_count=0 should not show '0 rules'."""
        evaluator = OWASPAgenticEvaluator()
        ctx = make_context()
        ev = make_evidence(has_guardrails=True, guardrail_count=0)
        results = evaluator.evaluate(ctx, ev)
        asi01 = _find(results, "ASI01")
        assert "0 rules" not in asi01.evidence
        assert "configured" in asi01.evidence.lower()

    def test_template_renders_without_error(self) -> None:
        """OWASP report_section.md.j2 should render with real evaluator data."""
        from jinja2 import Environment, FileSystemLoader

        evaluator = OWASPAgenticEvaluator()
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)

        # Build summary like Phase 6 would
        compliant = sum(1 for r in results if r.status == ComplianceStatus.COMPLIANT)
        partial = sum(1 for r in results if r.status == ComplianceStatus.PARTIAL)
        non_c = sum(1 for r in results if r.status == ComplianceStatus.NON_COMPLIANT)
        na = sum(1 for r in results if r.status == ComplianceStatus.NOT_APPLICABLE)
        ne = sum(1 for r in results if r.status == ComplianceStatus.NOT_EVALUATED)
        evaluated = len(results) - na - ne
        rate = (compliant / max(evaluated, 1)) * 100

        template_dir = Path(__file__).resolve().parent.parent.parent.parent / (
            "src/licit/frameworks/owasp_agentic/templates"
        )
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        template = env.get_template("report_section.md.j2")

        rendered = template.render(
            framework_name=evaluator.name,
            framework_version=evaluator.version,
            framework_description=evaluator.description,
            summary={
                "compliant": compliant,
                "partial": partial,
                "non_compliant": non_c,
                "not_applicable": na,
                "not_evaluated": ne,
                "total_controls": len(results),
                "compliance_rate": rate,
            },
            results=results,
        )

        assert "owasp-agentic" in rendered
        assert "ASI01" in rendered
        assert "ASI10" in rendered
        assert "Compliance rate" in rendered
        assert "non-compliant" in rendered


# ═══════════════════════════════════════════════════════════════════
# 5. Registry interop
# ═══════════════════════════════════════════════════════════════════


class TestFrameworkRegistry:
    def test_register_and_get_owasp(self) -> None:
        reg = FrameworkRegistry()
        evaluator = OWASPAgenticEvaluator()
        reg.register(evaluator)
        retrieved = reg.get("owasp-agentic")
        assert retrieved is not None
        assert retrieved.name == "owasp-agentic"

    def test_register_both_frameworks(self) -> None:
        from licit.frameworks.eu_ai_act.evaluator import EUAIActEvaluator

        reg = FrameworkRegistry()
        reg.register(EUAIActEvaluator())
        reg.register(OWASPAgenticEvaluator())
        assert len(reg.list_all()) == 2
        assert set(reg.names()) == {"eu-ai-act", "owasp-agentic"}

    def test_owasp_does_not_collide_with_eu_ai_act(self) -> None:
        from licit.frameworks.eu_ai_act.evaluator import EUAIActEvaluator

        reg = FrameworkRegistry()
        reg.register(EUAIActEvaluator())
        reg.register(OWASPAgenticEvaluator())
        eu = reg.get("eu-ai-act")
        owasp = reg.get("owasp-agentic")
        assert eu is not None and owasp is not None
        assert eu.name != owasp.name
        # Requirements should not overlap
        eu_ids = {r.id for r in eu.get_requirements()}
        owasp_ids = {r.id for r in owasp.get_requirements()}
        assert eu_ids.isdisjoint(owasp_ids)


# ═══════════════════════════════════════════════════════════════════
# 6. CLI integration
# ═══════════════════════════════════════════════════════════════════


class TestCLIIntegration:
    def test_verify_owasp_runs(self, tmp_path: Path) -> None:
        """licit verify --framework owasp should produce output and exit non-zero."""
        from licit.cli import main

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["verify", "--framework", "owasp"], obj={})
            assert result.exit_code in (1, 2)
            assert "Compliance Verification" in result.output

    def test_verify_all_includes_owasp(self, tmp_path: Path) -> None:
        """licit verify --framework all should include OWASP results."""
        from licit.cli import main

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["verify", "--framework", "all"], obj={})
            # Should have results from both frameworks
            assert result.exit_code in (1, 2)
            assert "Non-compliant" in result.output or "Partial" in result.output

    def test_verify_owasp_non_compliant_bare(self, tmp_path: Path) -> None:
        """A bare project should fail OWASP verify with exit code 1."""
        from licit.cli import main

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["verify", "--framework", "owasp"], obj={})
            assert result.exit_code == 1


# ═══════════════════════════════════════════════════════════════════
# 7. Requirements data integrity
# ═══════════════════════════════════════════════════════════════════


class TestRequirementsIntegrity:
    def test_all_requirement_ids_have_evaluator_method(self) -> None:
        """Every requirement should have a corresponding _eval_* method."""
        evaluator = OWASPAgenticEvaluator()
        for req in REQUIREMENTS:
            method_name = f"_eval_{req.id.lower()}"
            method = getattr(evaluator, method_name, None)
            assert method is not None, (
                f"Missing evaluator method {method_name} for requirement {req.id}"
            )

    def test_requirement_frameworks_consistent(self) -> None:
        for req in REQUIREMENTS:
            assert req.framework == "owasp-agentic"

    def test_categories_from_known_set(self) -> None:
        valid = {
            "access-control",
            "input-security",
            "supply-chain",
            "observability",
            "output-security",
            "human-oversight",
            "isolation",
            "resource-limits",
            "error-handling",
            "data-protection",
        }
        for req in REQUIREMENTS:
            assert req.category in valid, f"{req.id} has unknown category {req.category}"

    def test_ids_sequential(self) -> None:
        """IDs should be ASI01 through ASI10."""
        expected = {f"ASI{i:02d}" for i in range(1, 11)}
        actual = {r.id for r in REQUIREMENTS}
        assert actual == expected


# ═══════════════════════════════════════════════════════════════════
# 8. Cross-module compatibility
# ═══════════════════════════════════════════════════════════════════


class TestCrossModule:
    def test_results_compatible_with_gap_item(self) -> None:
        from licit.core.models import GapItem

        evaluator = OWASPAgenticEvaluator()
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        non_compliant = [r for r in results if r.status == ComplianceStatus.NON_COMPLIANT]
        assert len(non_compliant) > 0
        r = non_compliant[0]
        gap = GapItem(
            requirement=r.requirement,
            status=r.status,
            gap_description=r.evidence,
            recommendation=r.recommendations[0] if r.recommendations else "N/A",
            effort="medium",
        )
        assert gap.requirement.id == r.requirement.id

    def test_results_compatible_with_compliance_summary(self) -> None:
        from licit.core.models import ComplianceSummary

        evaluator = OWASPAgenticEvaluator()
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
            framework="owasp-agentic",
            total_controls=len(results),
            compliant=compliant,
            partial=partial,
            non_compliant=non_c,
            not_applicable=na,
            not_evaluated=ne,
            compliance_rate=rate,
        )
        assert summary.total_controls == 10

    def test_owasp_and_eu_ai_act_can_evaluate_same_context(self) -> None:
        """Both frameworks should evaluate the same context without conflict."""
        from licit.frameworks.eu_ai_act.evaluator import EUAIActEvaluator

        ctx = make_context()
        ev = make_evidence()
        owasp_results = OWASPAgenticEvaluator().evaluate(ctx, ev)
        eu_results = EUAIActEvaluator().evaluate(ctx, ev)

        assert len(owasp_results) == 10
        assert len(eu_results) == 11

        # No requirement ID collision
        owasp_ids = {r.requirement.id for r in owasp_results}
        eu_ids = {r.requirement.id for r in eu_results}
        assert owasp_ids.isdisjoint(eu_ids)


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


def _find(results: list[ControlResult], req_id: str) -> ControlResult:
    for r in results:
        if r.requirement.id == req_id:
            return r
    pytest.fail(f"No result found for {req_id}")
