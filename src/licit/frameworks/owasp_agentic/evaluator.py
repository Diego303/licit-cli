"""Evaluate project compliance against OWASP Agentic Top 10 risks."""

from __future__ import annotations

import structlog

from licit.core.evidence import EvidenceBundle
from licit.core.models import ComplianceStatus, ControlRequirement, ControlResult
from licit.core.project import ProjectContext
from licit.frameworks.owasp_agentic.requirements import (
    OWASP_AGENTIC_FRAMEWORK,
    OWASP_AGENTIC_VERSION,
    REQUIREMENTS,
)

logger = structlog.get_logger()


class OWASPAgenticEvaluator:
    """Evaluates project security posture against OWASP Agentic Top 10.

    Each risk is evaluated by a dedicated method that scores the project
    based on evidence collected from the project context and evidence bundle.
    """

    @property
    def name(self) -> str:
        return OWASP_AGENTIC_FRAMEWORK

    @property
    def version(self) -> str:
        return OWASP_AGENTIC_VERSION

    @property
    def description(self) -> str:
        return "OWASP Top 10 for Agentic AI Security"

    def get_requirements(self) -> list[ControlRequirement]:
        """Return all evaluable requirements."""
        return list(REQUIREMENTS)

    def evaluate(
        self,
        context: ProjectContext,
        evidence: EvidenceBundle,
    ) -> list[ControlResult]:
        """Evaluate all controls against project evidence."""
        results: list[ControlResult] = []
        for req in REQUIREMENTS:
            method_name = f"_eval_{req.id.lower()}"
            evaluator = getattr(self, method_name, None)
            if evaluator is not None:
                result: ControlResult = evaluator(req, context, evidence)
                results.append(result)
            else:
                results.append(ControlResult(
                    requirement=req,
                    status=ComplianceStatus.NOT_EVALUATED,
                    evidence="No automated evaluation available for this control.",
                    recommendations=["Manual assessment required."],
                ))

        evaluated = sum(1 for r in results if r.status != ComplianceStatus.NOT_EVALUATED)
        logger.info(
            "owasp_agentic_evaluation_complete",
            total=len(results),
            evaluated=evaluated,
        )
        return results

    # ── ASI01: Excessive Agency ─────────────────────────────────────

    def _eval_asi01(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """ASI-01 — Excessive Agency.

        Scoring (max 4): guardrails +1, quality gates +1, budget limits +1,
        agent configs with constraints +1.
        Compliant at 3+ (principle of least privilege enforced),
        partial at 1+ (some restrictions in place).
        """
        indicators: list[str] = []
        score = 0

        if ev.has_guardrails:
            if ev.guardrail_count:
                indicators.append(f"Guardrails limit agent scope: {ev.guardrail_count} rules")
            else:
                indicators.append("Guardrails configured (no specific rules counted)")
            score += 1
        if ev.has_quality_gates:
            indicators.append(f"Quality gates restrict output: {ev.quality_gate_count} gates")
            score += 1
        if ev.has_budget_limits:
            indicators.append("Budget limits cap resource usage")
            score += 1
        if ctx.agent_configs:
            indicators.append(
                f"Agent behavior defined in {len(ctx.agent_configs)} config file(s)"
            )
            score += 1

        status = _score_to_status(score, compliant_at=3, partial_at=1)

        recs: list[str] = []
        if not ev.has_guardrails:
            recs.append(
                "Add guardrails: protected files, blocked commands, "
                "or tool allowlists to limit agent actions"
            )
        if not ev.has_budget_limits:
            recs.append("Set budget limits to cap token/cost usage per session")

        return ControlResult(
            requirement=req,
            status=status,
            evidence=(
                "; ".join(indicators)
                if indicators
                else "No agency restrictions detected"
            ),
            recommendations=recs,
        )

    # ── ASI02: Prompt Injection ─────────────────────────────────────

    def _eval_asi02(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """ASI-02 — Prompt Injection.

        Scoring (max 4): security scanning (vigil) +2, guardrails +1,
        human review gate +1.
        Compliant at 3+ (active defense), partial at 1+.
        """
        indicators: list[str] = []
        score = 0

        if ctx.security.has_vigil:
            indicators.append("vigil scans for prompt injection patterns")
            score += 2
        if ev.has_guardrails:
            indicators.append("Guardrails constrain agent input handling")
            score += 1
        if ev.has_human_review_gate:
            indicators.append("Human review catches injected content before merge")
            score += 1

        status = _score_to_status(score, compliant_at=3, partial_at=1)

        recs: list[str] = []
        if not ctx.security.has_vigil:
            recs.append(
                "Add AI-specific security scanning: vigil detects prompt injection, "
                "jailbreak, and data exfiltration patterns"
            )
        if not ev.has_guardrails:
            recs.append("Add input guardrails to filter adversarial content")

        return ControlResult(
            requirement=req,
            status=status,
            evidence=(
                "; ".join(indicators)
                if indicators
                else "No prompt injection defenses detected"
            ),
            recommendations=recs,
        )

    # ── ASI03: Supply Chain Vulnerabilities ─────────────────────────

    def _eval_asi03(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """ASI-03 — Supply Chain Vulnerabilities.

        Scoring (max 4): SCA tools (snyk/semgrep) +2, changelog tracking +1,
        agent configs versioned +1.
        Compliant at 3+, partial at 1+.
        """
        indicators: list[str] = []
        score = 0

        sca_tools: list[str] = []
        if ctx.security.has_snyk:
            sca_tools.append("Snyk")
        if ctx.security.has_semgrep:
            sca_tools.append("Semgrep")
        if ctx.security.has_codeql:
            sca_tools.append("CodeQL")
        if ctx.security.has_trivy:
            sca_tools.append("Trivy")
        if sca_tools:
            indicators.append(f"Dependency scanning: {', '.join(sca_tools)}")
            score += 2

        if ev.has_changelog:
            indicators.append(
                f"Agent config changes tracked: {ev.changelog_entry_count} entries"
            )
            score += 1
        if ctx.agent_configs:
            indicators.append(
                f"{len(ctx.agent_configs)} agent config(s) under version control"
            )
            score += 1

        status = _score_to_status(score, compliant_at=3, partial_at=1)

        recs: list[str] = []
        if not sca_tools:
            recs.append(
                "Add dependency scanning: Snyk, Semgrep, or Trivy "
                "to detect vulnerable dependencies"
            )
        if not ev.has_changelog:
            recs.append("Run: licit changelog -- to track agent config changes over time")

        return ControlResult(
            requirement=req,
            status=status,
            evidence=(
                "; ".join(indicators)
                if indicators
                else "No supply chain controls detected"
            ),
            recommendations=recs,
        )

    # ── ASI04: Insufficient Logging and Monitoring ──────────────────

    def _eval_asi04(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """ASI-04 — Insufficient Logging and Monitoring.

        Scoring (max 5): git +1, audit trail +2 (structured is high-value),
        provenance +1, OTel +1.
        Compliant at 3+, partial at 1+.
        """
        indicators: list[str] = []
        score = 0

        if ctx.git_initialized:
            indicators.append(f"Git history: {ctx.total_commits} commits tracked")
            score += 1
        if ev.has_audit_trail:
            indicators.append(
                f"Structured audit trail: {ev.audit_entry_count} entries"
            )
            score += 2
        if ev.has_provenance:
            ai_pct = _safe_float(
                ev.provenance_stats.get("ai_percentage", 0), field="ai_percentage"
            )
            indicators.append(f"Code provenance tracking: {ai_pct:.0f}% AI attribution")
            score += 1
        if ev.has_otel:
            indicators.append("OpenTelemetry traces configured")
            score += 1

        status = _score_to_status(score, compliant_at=3, partial_at=1)

        recs: list[str] = []
        if not ev.has_audit_trail:
            recs.append(
                "Enable structured audit trail "
                "(architect reports or structured logging)"
            )
        if not ev.has_provenance:
            recs.append("Run: licit trace -- to start tracking code provenance")

        return ControlResult(
            requirement=req,
            status=status,
            evidence=(
                "; ".join(indicators)
                if indicators
                else "No logging or monitoring detected"
            ),
            recommendations=recs,
        )

    # ── ASI05: Improper Output Handling ─────────────────────────────

    def _eval_asi05(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """ASI-05 — Improper Output Handling.

        Scoring (max 4): human review gate +2, quality gates +1,
        test framework +1.
        Compliant at 3+, partial at 1+.
        """
        indicators: list[str] = []
        score = 0

        if ev.has_human_review_gate:
            indicators.append("Human review validates AI output before merge")
            score += 2
        if ev.has_quality_gates:
            indicators.append(
                f"Quality gates verify output: {ev.quality_gate_count} checks"
            )
            score += 1
        if ctx.test_framework:
            indicators.append(
                f"Test suite validates behavior: {ctx.test_framework}"
            )
            score += 1

        status = _score_to_status(score, compliant_at=3, partial_at=1)

        recs: list[str] = []
        if not ev.has_human_review_gate:
            recs.append(
                "Require human review for AI-generated code "
                "before it reaches production"
            )
        if not ctx.test_framework:
            recs.append("Add automated tests to validate AI-generated output")

        return ControlResult(
            requirement=req,
            status=status,
            evidence=(
                "; ".join(indicators)
                if indicators
                else "No output validation mechanisms detected"
            ),
            recommendations=recs,
        )

    # ── ASI06: Lack of Human Oversight ──────────────────────────────

    def _eval_asi06(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """ASI-06 — Lack of Human Oversight.

        Scoring (max 5): human review gate +2 (critical),
        dry-run +1, quality gates +1, rollback +1.
        Compliant at 3+, partial at 1+.
        """
        indicators: list[str] = []
        score = 0

        if ev.has_human_review_gate:
            indicators.append("Human review required before merge")
            score += 2
        if ev.has_dry_run:
            indicators.append("Dry-run mode enables preview without execution")
            score += 1
        if ev.has_quality_gates:
            indicators.append("Quality gates prevent unverified code")
            score += 1
        if ev.has_rollback:
            indicators.append("Rollback capability for reverting agent changes")
            score += 1

        status = _score_to_status(score, compliant_at=3, partial_at=1)

        recs: list[str] = []
        if not ev.has_human_review_gate:
            recs.append(
                "Enable PR review requirements so humans approve "
                "AI-generated changes"
            )
        if not ev.has_dry_run:
            recs.append("Enable dry-run mode to preview agent actions before execution")

        return ControlResult(
            requirement=req,
            status=status,
            evidence=(
                "; ".join(indicators)
                if indicators
                else "No human oversight mechanisms detected"
            ),
            recommendations=recs,
        )

    # ── ASI07: Insufficient Sandboxing ──────────────────────────────

    def _eval_asi07(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """ASI-07 — Insufficient Sandboxing.

        Scoring (max 4): guardrails (blocked commands / protected files) +2,
        CI/CD pipeline (isolated execution) +1, agent configs +1.
        Compliant at 3+, partial at 1+.
        """
        indicators: list[str] = []
        score = 0

        if ev.has_guardrails:
            if ev.guardrail_count:
                indicators.append(
                    f"Agent sandboxed via guardrails: {ev.guardrail_count} rules "
                    "(blocked commands, protected files)"
                )
            else:
                indicators.append("Agent sandboxed via guardrails (configured)")
            score += 2
        if ctx.cicd.platform != "none":
            indicators.append(
                f"CI/CD ({ctx.cicd.platform}) provides isolated execution environment"
            )
            score += 1
        if ctx.agent_configs:
            indicators.append("Agent scope defined in configuration files")
            score += 1

        status = _score_to_status(score, compliant_at=3, partial_at=1)

        recs: list[str] = []
        if not ev.has_guardrails:
            recs.append(
                "Add guardrails: block dangerous commands (rm -rf, chmod 777), "
                "protect sensitive files (.env, credentials)"
            )
        if ctx.cicd.platform == "none":
            recs.append("Set up CI/CD to run agents in isolated environments")

        return ControlResult(
            requirement=req,
            status=status,
            evidence=(
                "; ".join(indicators)
                if indicators
                else "No sandboxing or isolation controls detected"
            ),
            recommendations=recs,
        )

    # ── ASI08: Unbounded Resource Consumption ───────────────────────

    def _eval_asi08(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """ASI-08 — Unbounded Resource Consumption.

        Scoring (max 3): budget limits +2 (direct control),
        quality gates +1 (indirect bound).
        Compliant at 2+, partial at 1+.
        """
        indicators: list[str] = []
        score = 0

        if ev.has_budget_limits:
            indicators.append("Budget limits cap token/cost usage per session")
            score += 2
        if ev.has_quality_gates:
            indicators.append("Quality gates bound output scope")
            score += 1

        status = _score_to_status(score, compliant_at=2, partial_at=1)

        recs: list[str] = []
        if not ev.has_budget_limits:
            recs.append(
                "Set explicit budget limits (max cost, max tokens, max duration) "
                "to prevent runaway agent execution"
            )

        return ControlResult(
            requirement=req,
            status=status,
            evidence=(
                "; ".join(indicators)
                if indicators
                else "No resource consumption limits detected"
            ),
            recommendations=recs,
        )

    # ── ASI09: Poor Error Handling ──────────────────────────────────

    def _eval_asi09(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """ASI-09 — Poor Error Handling.

        Scoring (max 3): test suite +1, CI/CD +1, rollback +1.
        Compliant at 2+, partial at 1+.
        """
        indicators: list[str] = []
        score = 0

        if ctx.test_framework:
            test_dirs = ", ".join(ctx.test_dirs) if ctx.test_dirs else "detected"
            indicators.append(
                f"Test suite validates error paths: {ctx.test_framework} ({test_dirs})"
            )
            score += 1
        if ctx.cicd.platform != "none":
            indicators.append(f"CI/CD ({ctx.cicd.platform}) catches failures before deploy")
            score += 1
        if ev.has_rollback:
            indicators.append("Rollback capability for recovery from agent errors")
            score += 1

        status = _score_to_status(score, compliant_at=2, partial_at=1)

        recs: list[str] = []
        if not ctx.test_framework:
            recs.append("Add test suite to validate agent error handling paths")
        if not ev.has_rollback:
            recs.append("Implement rollback capability for failed agent operations")

        return ControlResult(
            requirement=req,
            status=status,
            evidence=(
                "; ".join(indicators)
                if indicators
                else "No error handling safeguards detected"
            ),
            recommendations=recs,
        )

    # ── ASI10: Sensitive Data Exposure ──────────────────────────────

    def _eval_asi10(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """ASI-10 — Sensitive Data Exposure.

        Scoring (max 4): guardrails (protected files) +1,
        security scanning +2, agent configs +1.
        Compliant at 3+, partial at 1+.
        """
        indicators: list[str] = []
        score = 0

        if ev.has_guardrails:
            indicators.append(
                "Guardrails protect sensitive files from agent access"
            )
            score += 1

        security_tools: list[str] = []
        if ctx.security.has_vigil:
            security_tools.append("vigil")
        if ctx.security.has_semgrep:
            security_tools.append("Semgrep")
        if ctx.security.has_snyk:
            security_tools.append("Snyk")
        if security_tools:
            indicators.append(f"Security scanning: {', '.join(security_tools)}")
            score += 2

        if ctx.agent_configs:
            indicators.append("Agent scope constrained by configuration")
            score += 1

        status = _score_to_status(score, compliant_at=3, partial_at=1)

        recs: list[str] = []
        if not ev.has_guardrails:
            recs.append(
                "Add protected file rules to prevent agent access to "
                ".env, credentials, and secrets"
            )
        if not security_tools:
            recs.append(
                "Add security scanning to detect data exposure: "
                "vigil, Semgrep, or Snyk"
            )

        return ControlResult(
            requirement=req,
            status=status,
            evidence=(
                "; ".join(indicators)
                if indicators
                else "No data exposure controls detected"
            ),
            recommendations=recs,
        )


def _score_to_status(
    score: int,
    *,
    compliant_at: int,
    partial_at: int,
) -> ComplianceStatus:
    """Convert a numeric score to a ComplianceStatus."""
    if score >= compliant_at:
        return ComplianceStatus.COMPLIANT
    if score >= partial_at:
        return ComplianceStatus.PARTIAL
    return ComplianceStatus.NON_COMPLIANT


def _safe_float(value: object, *, field: str = "unknown") -> float:
    """Safely convert a value to float, defaulting to 0.0."""
    if isinstance(value, (int, float)):
        return float(value)
    logger.debug(
        "unexpected_value_type",
        field=field,
        value_type=type(value).__name__,
    )
    return 0.0
