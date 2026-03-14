"""Tests for the OWASP Agentic Top 10 evaluator."""

from __future__ import annotations

import pytest

from licit.core.models import ComplianceStatus, ControlResult
from licit.core.project import AgentConfigFile, SecurityTooling
from licit.frameworks.owasp_agentic.evaluator import OWASPAgenticEvaluator
from licit.frameworks.owasp_agentic.requirements import REQUIREMENTS
from tests.conftest import make_context, make_evidence


@pytest.fixture
def evaluator() -> OWASPAgenticEvaluator:
    return OWASPAgenticEvaluator()


# ── Properties ─────────────────────────────────────────────────────


class TestEvaluatorProperties:
    def test_name(self, evaluator: OWASPAgenticEvaluator) -> None:
        assert evaluator.name == "owasp-agentic"

    def test_version(self, evaluator: OWASPAgenticEvaluator) -> None:
        assert evaluator.version == "2025"

    def test_description(self, evaluator: OWASPAgenticEvaluator) -> None:
        assert "OWASP" in evaluator.description

    def test_get_requirements_returns_all(self, evaluator: OWASPAgenticEvaluator) -> None:
        reqs = evaluator.get_requirements()
        assert len(reqs) == 10
        ids = {r.id for r in reqs}
        assert "ASI01" in ids
        assert "ASI10" in ids


# ── Full evaluation ────────────────────────────────────────────────


class TestEvaluateAll:
    def test_all_requirements_are_evaluated(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        assert len(results) == len(REQUIREMENTS)
        req_ids = {r.requirement.id for r in results}
        for req in REQUIREMENTS:
            assert req.id in req_ids

    def test_results_have_valid_status(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        valid = set(ComplianceStatus)
        for r in results:
            assert r.status in valid

    def test_results_have_evidence(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        for r in results:
            assert r.evidence, f"Result for {r.requirement.id} has empty evidence"

    def test_bare_minimum_project_mostly_non_compliant(
        self, evaluator: OWASPAgenticEvaluator
    ) -> None:
        """A bare project with no tooling should have many non-compliant results."""
        ctx = make_context(
            git_initialized=False,
            total_commits=0,
            agent_configs=[],
        )
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        non_compliant = [r for r in results if r.status == ComplianceStatus.NON_COMPLIANT]
        assert len(non_compliant) >= 5

    def test_well_configured_project_mostly_compliant(
        self, evaluator: OWASPAgenticEvaluator
    ) -> None:
        """A project with full tooling should mostly pass."""
        ctx = make_context(
            agent_configs=[AgentConfigFile(path="CLAUDE.md", agent_type="claude-code")],
            cicd_platform="github-actions",
            security=SecurityTooling(
                has_vigil=True, has_semgrep=True, has_snyk=True
            ),
        )
        ev = make_evidence(
            has_guardrails=True,
            guardrail_count=10,
            has_quality_gates=True,
            quality_gate_count=3,
            has_budget_limits=True,
            has_human_review_gate=True,
            has_dry_run=True,
            has_rollback=True,
            has_audit_trail=True,
            audit_entry_count=50,
            has_provenance=True,
            provenance_stats={"ai_percentage": 30.0},
            has_changelog=True,
            changelog_entry_count=5,
        )
        results = evaluator.evaluate(ctx, ev)
        compliant = [r for r in results if r.status == ComplianceStatus.COMPLIANT]
        assert len(compliant) >= 8


# ── ASI01: Excessive Agency ────────────────────────────────────────


class TestASI01:
    def test_compliant_with_full_controls(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context(
            agent_configs=[AgentConfigFile(path="CLAUDE.md", agent_type="claude-code")]
        )
        ev = make_evidence(
            has_guardrails=True, guardrail_count=10,
            has_quality_gates=True, quality_gate_count=3,
            has_budget_limits=True,
        )
        results = evaluator.evaluate(ctx, ev)
        asi01 = _find(results, "ASI01")
        assert asi01.status == ComplianceStatus.COMPLIANT
        assert "Guardrails" in asi01.evidence
        assert not asi01.recommendations

    def test_partial_with_guardrails_only(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence(has_guardrails=True, guardrail_count=3)
        results = evaluator.evaluate(ctx, ev)
        asi01 = _find(results, "ASI01")
        assert asi01.status == ComplianceStatus.PARTIAL

    def test_non_compliant_bare(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context(agent_configs=[])
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi01 = _find(results, "ASI01")
        assert asi01.status == ComplianceStatus.NON_COMPLIANT
        assert asi01.recommendations


# ── ASI02: Prompt Injection ────────────────────────────────────────


class TestASI02:
    def test_compliant_with_vigil_and_guardrails(
        self, evaluator: OWASPAgenticEvaluator
    ) -> None:
        ctx = make_context(security=SecurityTooling(has_vigil=True))
        ev = make_evidence(has_guardrails=True, has_human_review_gate=True)
        results = evaluator.evaluate(ctx, ev)
        asi02 = _find(results, "ASI02")
        assert asi02.status == ComplianceStatus.COMPLIANT
        assert "vigil" in asi02.evidence

    def test_partial_with_guardrails_only(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence(has_guardrails=True)
        results = evaluator.evaluate(ctx, ev)
        asi02 = _find(results, "ASI02")
        assert asi02.status == ComplianceStatus.PARTIAL

    def test_non_compliant_bare(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi02 = _find(results, "ASI02")
        assert asi02.status == ComplianceStatus.NON_COMPLIANT
        assert any("vigil" in r.lower() for r in asi02.recommendations)


# ── ASI03: Supply Chain Vulnerabilities ────────────────────────────


class TestASI03:
    def test_compliant_with_sca_and_changelog(
        self, evaluator: OWASPAgenticEvaluator
    ) -> None:
        ctx = make_context(
            security=SecurityTooling(has_snyk=True, has_semgrep=True),
            agent_configs=[AgentConfigFile(path="CLAUDE.md", agent_type="claude-code")],
        )
        ev = make_evidence(has_changelog=True, changelog_entry_count=5)
        results = evaluator.evaluate(ctx, ev)
        asi03 = _find(results, "ASI03")
        assert asi03.status == ComplianceStatus.COMPLIANT
        assert "Snyk" in asi03.evidence

    def test_partial_with_configs_only(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context(
            agent_configs=[AgentConfigFile(path="CLAUDE.md", agent_type="claude-code")]
        )
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi03 = _find(results, "ASI03")
        assert asi03.status == ComplianceStatus.PARTIAL

    def test_non_compliant_bare(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context(agent_configs=[])
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi03 = _find(results, "ASI03")
        assert asi03.status == ComplianceStatus.NON_COMPLIANT


# ── ASI04: Insufficient Logging and Monitoring ─────────────────────


class TestASI04:
    def test_compliant_with_full_logging(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context(git_initialized=True, total_commits=100)
        ev = make_evidence(
            has_audit_trail=True, audit_entry_count=50,
            has_provenance=True, provenance_stats={"ai_percentage": 30.0},
        )
        results = evaluator.evaluate(ctx, ev)
        asi04 = _find(results, "ASI04")
        assert asi04.status == ComplianceStatus.COMPLIANT
        assert "Git history" in asi04.evidence

    def test_partial_with_git_only(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context(git_initialized=True, total_commits=50)
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi04 = _find(results, "ASI04")
        assert asi04.status == ComplianceStatus.PARTIAL

    def test_non_compliant_without_git(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context(git_initialized=False, total_commits=0)
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi04 = _find(results, "ASI04")
        assert asi04.status == ComplianceStatus.NON_COMPLIANT

    def test_provenance_percentage_display(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence(
            has_provenance=True, provenance_stats={"ai_percentage": 55.0}
        )
        results = evaluator.evaluate(ctx, ev)
        asi04 = _find(results, "ASI04")
        assert "55%" in asi04.evidence


# ── ASI05: Improper Output Handling ────────────────────────────────


class TestASI05:
    def test_compliant_with_review_and_tests(
        self, evaluator: OWASPAgenticEvaluator
    ) -> None:
        ctx = make_context()
        ev = make_evidence(
            has_human_review_gate=True,
            has_quality_gates=True, quality_gate_count=3,
        )
        results = evaluator.evaluate(ctx, ev)
        asi05 = _find(results, "ASI05")
        assert asi05.status == ComplianceStatus.COMPLIANT

    def test_partial_with_tests_only(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx_with_tests = make_context()
        ctx_with_tests.test_framework = "pytest"
        ev = make_evidence()
        results = evaluator.evaluate(ctx_with_tests, ev)
        asi05 = _find(results, "ASI05")
        assert asi05.status == ComplianceStatus.PARTIAL

    def test_non_compliant_bare(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi05 = _find(results, "ASI05")
        assert asi05.status == ComplianceStatus.NON_COMPLIANT
        assert asi05.recommendations


# ── ASI06: Lack of Human Oversight ─────────────────────────────────


class TestASI06:
    def test_compliant_with_full_oversight(
        self, evaluator: OWASPAgenticEvaluator
    ) -> None:
        ctx = make_context()
        ev = make_evidence(
            has_human_review_gate=True,
            has_dry_run=True,
            has_quality_gates=True,
            has_rollback=True,
        )
        results = evaluator.evaluate(ctx, ev)
        asi06 = _find(results, "ASI06")
        assert asi06.status == ComplianceStatus.COMPLIANT

    def test_partial_with_review_only(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence(has_human_review_gate=True)
        results = evaluator.evaluate(ctx, ev)
        asi06 = _find(results, "ASI06")
        assert asi06.status == ComplianceStatus.PARTIAL

    def test_non_compliant_bare(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi06 = _find(results, "ASI06")
        assert asi06.status == ComplianceStatus.NON_COMPLIANT


# ── ASI07: Insufficient Sandboxing ─────────────────────────────────


class TestASI07:
    def test_compliant_with_guardrails_and_cicd(
        self, evaluator: OWASPAgenticEvaluator
    ) -> None:
        ctx = make_context(
            cicd_platform="github-actions",
            agent_configs=[AgentConfigFile(path="CLAUDE.md", agent_type="claude-code")],
        )
        ev = make_evidence(has_guardrails=True, guardrail_count=8)
        results = evaluator.evaluate(ctx, ev)
        asi07 = _find(results, "ASI07")
        assert asi07.status == ComplianceStatus.COMPLIANT

    def test_partial_with_cicd_only(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context(cicd_platform="github-actions")
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi07 = _find(results, "ASI07")
        assert asi07.status == ComplianceStatus.PARTIAL

    def test_non_compliant_bare(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context(cicd_platform="none", agent_configs=[])
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi07 = _find(results, "ASI07")
        assert asi07.status == ComplianceStatus.NON_COMPLIANT
        assert any("guardrails" in r.lower() for r in asi07.recommendations)


# ── ASI08: Unbounded Resource Consumption ──────────────────────────


class TestASI08:
    def test_compliant_with_budget_and_gates(
        self, evaluator: OWASPAgenticEvaluator
    ) -> None:
        ctx = make_context()
        ev = make_evidence(has_budget_limits=True, has_quality_gates=True)
        results = evaluator.evaluate(ctx, ev)
        asi08 = _find(results, "ASI08")
        assert asi08.status == ComplianceStatus.COMPLIANT

    def test_partial_with_gates_only(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence(has_quality_gates=True, quality_gate_count=2)
        results = evaluator.evaluate(ctx, ev)
        asi08 = _find(results, "ASI08")
        assert asi08.status == ComplianceStatus.PARTIAL

    def test_non_compliant_bare(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context()
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi08 = _find(results, "ASI08")
        assert asi08.status == ComplianceStatus.NON_COMPLIANT
        assert any("budget" in r.lower() for r in asi08.recommendations)


# ── ASI09: Poor Error Handling ─────────────────────────────────────


class TestASI09:
    def test_compliant_with_tests_cicd_rollback(
        self, evaluator: OWASPAgenticEvaluator
    ) -> None:
        ctx = make_context(cicd_platform="github-actions")
        ctx.test_framework = "pytest"
        ctx.test_dirs = ["tests"]
        ev = make_evidence(has_rollback=True)
        results = evaluator.evaluate(ctx, ev)
        asi09 = _find(results, "ASI09")
        assert asi09.status == ComplianceStatus.COMPLIANT

    def test_partial_with_cicd_only(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context(cicd_platform="github-actions")
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi09 = _find(results, "ASI09")
        assert asi09.status == ComplianceStatus.PARTIAL

    def test_non_compliant_bare(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context(cicd_platform="none")
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi09 = _find(results, "ASI09")
        assert asi09.status == ComplianceStatus.NON_COMPLIANT


# ── ASI10: Sensitive Data Exposure ─────────────────────────────────


class TestASI10:
    def test_compliant_with_guardrails_and_scanning(
        self, evaluator: OWASPAgenticEvaluator
    ) -> None:
        ctx = make_context(
            security=SecurityTooling(has_vigil=True, has_semgrep=True),
            agent_configs=[AgentConfigFile(path="CLAUDE.md", agent_type="claude-code")],
        )
        ev = make_evidence(has_guardrails=True, guardrail_count=5)
        results = evaluator.evaluate(ctx, ev)
        asi10 = _find(results, "ASI10")
        assert asi10.status == ComplianceStatus.COMPLIANT

    def test_partial_with_configs_only(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context(
            agent_configs=[AgentConfigFile(path="CLAUDE.md", agent_type="claude-code")]
        )
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi10 = _find(results, "ASI10")
        assert asi10.status == ComplianceStatus.PARTIAL

    def test_non_compliant_bare(self, evaluator: OWASPAgenticEvaluator) -> None:
        ctx = make_context(agent_configs=[])
        ev = make_evidence()
        results = evaluator.evaluate(ctx, ev)
        asi10 = _find(results, "ASI10")
        assert asi10.status == ComplianceStatus.NON_COMPLIANT
        assert asi10.recommendations


# ── Helpers ────────────────────────────────────────────────────────


def _find(results: list[ControlResult], req_id: str) -> ControlResult:
    """Find a ControlResult by requirement ID."""
    for r in results:
        if r.requirement.id == req_id:
            return r
    pytest.fail(f"No result found for requirement {req_id}")
