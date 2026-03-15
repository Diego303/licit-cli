"""Gap analyzer — identifies missing compliance requirements with recommendations."""

from __future__ import annotations

from typing import Any

import structlog

from licit.config.schema import LicitConfig
from licit.core.evidence import EvidenceBundle
from licit.core.models import ComplianceStatus, ControlResult, GapItem
from licit.core.project import ProjectContext

logger = structlog.get_logger()

# Tool suggestions mapped to requirement categories.
# Keys MUST match the 'category' field in ControlRequirement instances
# defined in requirements.py for each framework.
_TOOL_SUGGESTIONS: dict[str, list[str]] = {
    # EU AI Act categories (from eu_ai_act/requirements.py)
    "risk-management": ["architect (guardrails)", "vigil (security scanning)"],
    "data-governance": ["licit annex-iv (document data practices)"],
    "record-keeping": ["licit trace", "architect (audit log)"],
    "transparency": ["licit annex-iv", "licit changelog"],
    "human-oversight": ["architect (dry-run)", "GitHub branch protection"],
    "deployer-obligations": ["licit init"],
    "fria": ["licit fria"],
    "documentation": ["licit annex-iv"],
    # OWASP Agentic categories (from owasp_agentic/requirements.py)
    "access-control": ["architect (guardrails)", "vigil"],
    "input-security": ["vigil (prompt injection scanner)"],
    "supply-chain": ["snyk", "pip-audit", "npm audit"],
    "observability": ["licit trace", "structlog", "OpenTelemetry"],
    "output-security": ["vigil (output validation)"],
    "isolation": ["architect (sandbox mode)", "Docker"],
    "resource-limits": ["architect (budget limits)"],
    "error-handling": ["structlog", "Sentry"],
    "data-protection": ["vigil (sensitive data scanner)", ".gitignore"],
}

# Effort estimates based on category.
# Keys MUST match _TOOL_SUGGESTIONS keys above.
_EFFORT_MAP: dict[str, str] = {
    # EU AI Act
    "risk-management": "medium",
    "data-governance": "low",
    "record-keeping": "low",
    "transparency": "low",
    "human-oversight": "medium",
    "deployer-obligations": "low",
    "fria": "medium",
    "documentation": "low",
    # OWASP Agentic
    "access-control": "medium",
    "input-security": "high",
    "supply-chain": "medium",
    "observability": "low",
    "output-security": "medium",
    "isolation": "high",
    "resource-limits": "low",
    "error-handling": "low",
    "data-protection": "medium",
}


class GapAnalyzer:
    """Identifies compliance gaps and provides actionable recommendations."""

    def __init__(
        self,
        context: ProjectContext,
        evidence: EvidenceBundle,
        config: LicitConfig,
    ) -> None:
        self.context = context
        self.evidence = evidence
        self.config = config

    def analyze(self, frameworks: list[Any]) -> list[GapItem]:
        """Evaluate frameworks and return gaps sorted by priority."""
        gaps: list[GapItem] = []

        for fw in frameworks:
            try:
                results: list[ControlResult] = fw.evaluate(self.context, self.evidence)
            except Exception:
                logger.exception("gap_analysis_framework_failed", framework=fw.name)
                continue

            for result in results:
                if result.status in (
                    ComplianceStatus.NON_COMPLIANT,
                    ComplianceStatus.PARTIAL,
                ):
                    gap = self._result_to_gap(result)
                    gaps.append(gap)

        # Sort: non-compliant first, then by priority (lower = higher priority)
        gaps.sort(
            key=lambda g: (
                0 if g.status == ComplianceStatus.NON_COMPLIANT else 1,
                g.priority,
            )
        )

        # Assign sequential priority
        for i, gap in enumerate(gaps):
            gap.priority = i + 1

        logger.info("gap_analysis_complete", total_gaps=len(gaps))
        return gaps

    def _result_to_gap(self, result: ControlResult) -> GapItem:
        """Convert a non-compliant or partial ControlResult into a GapItem."""
        category = result.requirement.category or ""

        recommendation = (
            result.recommendations[0]
            if result.recommendations
            else f"Address {result.requirement.name} to improve compliance."
        )

        tools = _TOOL_SUGGESTIONS.get(category, [])
        effort = _EFFORT_MAP.get(category, "medium")

        gap_description = self._build_gap_description(result)

        return GapItem(
            requirement=result.requirement,
            status=result.status,
            gap_description=gap_description,
            recommendation=recommendation,
            effort=effort,
            tools_suggested=list(tools),
        )

    def _build_gap_description(self, result: ControlResult) -> str:
        """Build a human-readable gap description from evaluation result."""
        if result.status == ComplianceStatus.NON_COMPLIANT:
            prefix = "Missing"
        else:
            prefix = "Incomplete"

        evidence_note = f" Evidence: {result.evidence}" if result.evidence else ""
        return f"{prefix}: {result.requirement.description}{evidence_note}"
