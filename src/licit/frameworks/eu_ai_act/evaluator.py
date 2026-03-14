"""Evaluate project compliance against EU AI Act articles."""

from __future__ import annotations

import structlog

from licit.core.evidence import EvidenceBundle
from licit.core.models import ComplianceStatus, ControlRequirement, ControlResult
from licit.core.project import ProjectContext
from licit.frameworks.eu_ai_act.requirements import (
    EU_AI_ACT_FRAMEWORK,
    EU_AI_ACT_VERSION,
    REQUIREMENTS,
)

logger = structlog.get_logger()


class EUAIActEvaluator:
    """Evaluates compliance with EU AI Act deployer obligations.

    Each article is evaluated by a dedicated method that scores the project
    based on evidence collected from the project context and evidence bundle.
    """

    @property
    def name(self) -> str:
        return EU_AI_ACT_FRAMEWORK

    @property
    def version(self) -> str:
        return EU_AI_ACT_VERSION

    @property
    def description(self) -> str:
        return "European Union Artificial Intelligence Act"

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
            method_name = f"_eval_{req.id.lower().replace('-', '_')}"
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
            "eu_ai_act_evaluation_complete",
            total=len(results),
            evaluated=evaluated,
        )
        return results

    # ── Article 9: Risk Management ─────────────────────────────────

    def _eval_art_9_1(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """Art. 9 — Risk Management System.

        Scoring (max 4): guardrails +1, quality gates +1, budget limits +1,
        security scanning +1.  Compliant at 3+ (most controls active),
        partial at 1+ (at least one measure in place).
        """
        indicators: list[str] = []
        score = 0

        if ev.has_guardrails:
            indicators.append(f"Guardrails active: {ev.guardrail_count} rules")
            score += 1
        if ev.has_quality_gates:
            indicators.append(f"Quality gates: {ev.quality_gate_count} gates")
            score += 1
        if ev.has_budget_limits:
            indicators.append("Budget limits configured")
            score += 1

        security_tools: list[str] = []
        if ctx.security.has_vigil:
            security_tools.append("vigil")
        if ctx.security.has_semgrep:
            security_tools.append("semgrep")
        if ctx.security.has_snyk:
            security_tools.append("snyk")
        if security_tools:
            indicators.append(f"Security scanning: {', '.join(security_tools)}")
            score += 1

        status = _score_to_status(score, compliant_at=3, partial_at=1)

        recs: list[str] = []
        if not ev.has_guardrails:
            recs.append(
                "Add guardrails to limit agent actions "
                "(architect, Claude Code hooks, or manual)"
            )
        if not security_tools:
            recs.append("Add security scanning (vigil, Semgrep, Snyk, or CodeQL)")

        return ControlResult(
            requirement=req,
            status=status,
            evidence=(
                "; ".join(indicators) if indicators else "No risk management measures detected"
            ),
            recommendations=recs,
        )

    # ── Article 10: Data Governance ────────────────────────────────

    def _eval_art_10_1(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """Art. 10 — Data Governance (deployer perspective)."""
        return ControlResult(
            requirement=req,
            status=ComplianceStatus.PARTIAL,
            evidence="Model provider manages training data. Deployer does not train models.",
            recommendations=["Document model provider's data governance practices"],
        )

    # ── Article 12: Record Keeping ─────────────────────────────────

    def _eval_art_12_1(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """Art. 12 — Record Keeping (Automatic Logging).

        Scoring (max 5): git +1, audit trail +2 (structured is high-value),
        provenance +1, OTel +1.  Compliant at 3+, partial at 1+.
        """
        indicators: list[str] = []
        score = 0

        if ctx.git_initialized:
            indicators.append(f"Git history: {ctx.total_commits} commits")
            score += 1
        if ev.has_audit_trail:
            indicators.append(f"Structured audit trail: {ev.audit_entry_count} entries")
            score += 2
        if ev.has_provenance:
            ai_pct_raw = ev.provenance_stats.get("ai_percentage", 0)
            if isinstance(ai_pct_raw, (int, float)):
                ai_pct = float(ai_pct_raw)
            else:
                logger.debug(
                    "unexpected_provenance_stats_type",
                    field="ai_percentage",
                    value_type=type(ai_pct_raw).__name__,
                )
                ai_pct = 0.0
            indicators.append(f"Provenance tracking: {ai_pct:.0f}% AI attribution")
            score += 1
        if ev.has_otel:
            indicators.append("OpenTelemetry traces configured")
            score += 1

        status = _score_to_status(score, compliant_at=3, partial_at=1)

        recs: list[str] = []
        if not ev.has_audit_trail:
            recs.append("Enable structured audit trail (architect reports or manual logging)")
        if not ev.has_provenance:
            recs.append("Run: licit trace -- to start tracking code provenance")

        return ControlResult(
            requirement=req,
            status=status,
            evidence="; ".join(indicators) if indicators else "No automatic logging detected",
            recommendations=recs,
        )

    # ── Article 13: Transparency ───────────────────────────────────

    def _eval_art_13_1(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """Art. 13 — Transparency (Information for Deployers).

        Scoring (max 4): annex IV +2 (core doc), changelog +1,
        requirements traceability +1.  Compliant at 2+ (Annex IV alone suffices),
        partial at 1+.
        """
        indicators: list[str] = []
        score = 0

        if ev.has_annex_iv:
            indicators.append("Annex IV technical documentation generated")
            score += 2
        if ev.has_changelog:
            indicators.append(f"Agent config changelog: {ev.changelog_entry_count} entries")
            score += 1
        if ev.has_requirements_traceability:
            indicators.append("Requirements traceability available (intake)")
            score += 1

        status = _score_to_status(score, compliant_at=2, partial_at=1)

        recs: list[str] = []
        if not ev.has_annex_iv:
            recs.append("Run: licit annex-iv -- to generate technical documentation")
        if not ev.has_changelog:
            recs.append("Run: licit changelog -- to track agent configuration changes")

        return ControlResult(
            requirement=req,
            status=status,
            evidence=(
                "; ".join(indicators) if indicators else "No transparency documentation found"
            ),
            recommendations=recs,
        )

    # ── Article 14: Human Oversight ────────────────────────────────

    def _eval_art_14_1(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """Art. 14 — Human Oversight.

        Scoring (max 5): dry-run +1, human review gate +2 (critical control),
        quality gates +1, budget limits +1.  Compliant at 3+, partial at 1+.
        """
        indicators: list[str] = []
        score = 0

        if ev.has_dry_run:
            indicators.append("Dry-run mode available")
            score += 1
        if ev.has_human_review_gate:
            indicators.append("Human review required before merge")
            score += 2
        if ev.has_quality_gates:
            indicators.append("Quality gates prevent unverified code")
            score += 1
        if ev.has_budget_limits:
            indicators.append("Budget limits prevent runaway execution")
            score += 1

        status = _score_to_status(score, compliant_at=3, partial_at=1)

        recs: list[str] = []
        if not ev.has_human_review_gate:
            recs.append("Enable PR review requirements for AI-generated branches")

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

    def _eval_art_14_4a(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """Art. 14(4)(a) — Human Oversight: Understand Capabilities."""
        # Same evidence as Art. 14(1) applies
        return self._eval_art_14_1(req, ctx, ev)

    def _eval_art_14_4d(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """Art. 14(4)(d) — Ability to Intervene (override/reverse)."""
        indicators: list[str] = []

        if ev.has_dry_run:
            indicators.append("Dry-run mode allows previewing without executing")
        if ev.has_rollback:
            indicators.append("Rollback capability available")

        return ControlResult(
            requirement=req,
            status=ComplianceStatus.COMPLIANT if indicators else ComplianceStatus.PARTIAL,
            evidence="; ".join(indicators) if indicators else "Basic git revert available",
            recommendations=[] if indicators else ["Consider adding rollback capabilities"],
        )

    # ── Article 26: Deployer Obligations ───────────────────────────

    def _eval_art_26_1(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """Art. 26(1) — Use in Accordance with Instructions."""
        has_configs = bool(ctx.agent_configs)
        return ControlResult(
            requirement=req,
            status=ComplianceStatus.COMPLIANT if has_configs else ComplianceStatus.PARTIAL,
            evidence=(
                f"{len(ctx.agent_configs)} agent configs detected"
                if has_configs
                else "No structured agent configuration found"
            ),
        )

    def _eval_art_26_5(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """Art. 26(5) — Deployer Monitoring (same as Art. 12 logging)."""
        return self._eval_art_12_1(req, ctx, ev)

    # ── Article 27: FRIA ───────────────────────────────────────────

    def _eval_art_27_1(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """Art. 27 — Fundamental Rights Impact Assessment."""
        if ev.has_fria:
            return ControlResult(
                requirement=req,
                status=ComplianceStatus.COMPLIANT,
                evidence=f"FRIA completed: {ev.fria_path}",
            )
        return ControlResult(
            requirement=req,
            status=ComplianceStatus.NON_COMPLIANT,
            evidence="No FRIA document found",
            recommendations=[
                "Run: licit fria -- to complete the Fundamental Rights Impact Assessment"
            ],
        )

    # ── Annex IV: Technical Documentation ──────────────────────────

    def _eval_annex_iv(
        self,
        req: ControlRequirement,
        ctx: ProjectContext,
        ev: EvidenceBundle,
    ) -> ControlResult:
        """Annex IV — Technical Documentation."""
        if ev.has_annex_iv:
            return ControlResult(
                requirement=req,
                status=ComplianceStatus.COMPLIANT,
                evidence=f"Annex IV documentation: {ev.annex_iv_path}",
            )
        return ControlResult(
            requirement=req,
            status=ComplianceStatus.NON_COMPLIANT,
            evidence="No Annex IV technical documentation found",
            recommendations=[
                "Run: licit annex-iv -- to generate technical documentation"
            ],
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
