"""Unified multi-framework compliance report generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from licit.config.schema import LicitConfig
from licit.core.evidence import EvidenceBundle
from licit.core.models import ComplianceStatus, ComplianceSummary, ControlResult
from licit.core.project import ProjectContext
from licit.frameworks.base import ComplianceFramework

logger = structlog.get_logger()


@dataclass
class FrameworkReport:
    """Evaluation results for a single framework."""

    name: str
    version: str
    description: str
    summary: ComplianceSummary
    results: list[ControlResult]


@dataclass
class UnifiedReport:
    """Complete unified compliance report across all frameworks."""

    project_name: str
    generated_at: str
    frameworks: list[FrameworkReport] = field(default_factory=list)
    overall_compliance_rate: float = 0.0
    overall_compliant: int = 0
    overall_partial: int = 0
    overall_non_compliant: int = 0
    overall_not_applicable: int = 0
    overall_not_evaluated: int = 0
    overall_total: int = 0
    include_evidence: bool = True
    include_recommendations: bool = True


class UnifiedReportGenerator:
    """Generates unified compliance reports across multiple frameworks."""

    def __init__(
        self,
        context: ProjectContext,
        evidence: EvidenceBundle,
        config: LicitConfig,
    ) -> None:
        self.context = context
        self.evidence = evidence
        self.config = config

    def generate(
        self,
        frameworks: list[Any],
    ) -> UnifiedReport:
        """Evaluate all frameworks and produce a unified report."""
        report = UnifiedReport(
            project_name=self.context.name,
            generated_at=datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC"),
            include_evidence=self.config.reports.include_evidence,
            include_recommendations=self.config.reports.include_recommendations,
        )

        for fw in frameworks:
            fw_report = self._evaluate_framework(fw)
            if fw_report is not None:
                report.frameworks.append(fw_report)

        self._compute_overall(report)

        logger.info(
            "report_generated",
            frameworks=len(report.frameworks),
            compliance_rate=report.overall_compliance_rate,
        )
        return report

    def _evaluate_framework(
        self, fw: ComplianceFramework,
    ) -> FrameworkReport | None:
        """Evaluate a single framework and build its report section.

        Returns None if the framework evaluator raises an exception,
        allowing the report to proceed with remaining frameworks.
        """
        try:
            results = fw.evaluate(self.context, self.evidence)
        except Exception:
            logger.exception("framework_evaluation_failed", framework=fw.name)
            return None

        summary = self._summarize(fw.name, results)

        return FrameworkReport(
            name=fw.name,
            version=fw.version,
            description=fw.description,
            summary=summary,
            results=results,
        )

    def _summarize(self, framework: str, results: list[ControlResult]) -> ComplianceSummary:
        """Compute summary statistics from evaluation results."""
        compliant = sum(1 for r in results if r.status == ComplianceStatus.COMPLIANT)
        partial = sum(1 for r in results if r.status == ComplianceStatus.PARTIAL)
        non_compliant = sum(1 for r in results if r.status == ComplianceStatus.NON_COMPLIANT)
        not_applicable = sum(1 for r in results if r.status == ComplianceStatus.NOT_APPLICABLE)
        not_evaluated = sum(1 for r in results if r.status == ComplianceStatus.NOT_EVALUATED)

        evaluated = compliant + partial + non_compliant
        rate = (compliant / evaluated * 100) if evaluated > 0 else 0.0

        return ComplianceSummary(
            framework=framework,
            total_controls=len(results),
            compliant=compliant,
            partial=partial,
            non_compliant=non_compliant,
            not_applicable=not_applicable,
            not_evaluated=not_evaluated,
            compliance_rate=round(rate, 1),
        )

    def _compute_overall(self, report: UnifiedReport) -> None:
        """Aggregate statistics across all frameworks."""
        for fw_report in report.frameworks:
            s = fw_report.summary
            report.overall_compliant += s.compliant
            report.overall_partial += s.partial
            report.overall_non_compliant += s.non_compliant
            report.overall_not_applicable += s.not_applicable
            report.overall_not_evaluated += s.not_evaluated
            report.overall_total += s.total_controls

        evaluated = (
            report.overall_compliant + report.overall_partial + report.overall_non_compliant
        )
        report.overall_compliance_rate = (
            round(report.overall_compliant / evaluated * 100, 1) if evaluated > 0 else 0.0
        )
