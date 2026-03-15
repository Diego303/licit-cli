"""JSON report renderer for unified compliance reports."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from licit.reports.unified import FrameworkReport, UnifiedReport


def render(report: UnifiedReport) -> str:
    """Render a UnifiedReport as JSON."""
    data = _report_to_dict(report)
    return json.dumps(data, indent=2, default=_json_default, ensure_ascii=False)


def _report_to_dict(report: UnifiedReport) -> dict[str, Any]:
    """Convert UnifiedReport to a JSON-serializable dict."""
    return {
        "project_name": report.project_name,
        "generated_at": report.generated_at,
        "overall": {
            "total_controls": report.overall_total,
            "compliant": report.overall_compliant,
            "partial": report.overall_partial,
            "non_compliant": report.overall_non_compliant,
            "not_applicable": report.overall_not_applicable,
            "not_evaluated": report.overall_not_evaluated,
            "compliance_rate": report.overall_compliance_rate,
        },
        "frameworks": [
            _framework_to_dict(fw, report.include_evidence, report.include_recommendations)
            for fw in report.frameworks
        ],
    }


def _framework_to_dict(
    fw: FrameworkReport,
    include_evidence: bool,
    include_recommendations: bool,
) -> dict[str, Any]:
    """Convert a FrameworkReport to dict."""
    results_list: list[dict[str, Any]] = []
    for r in fw.results:
        entry: dict[str, Any] = {
            "id": r.requirement.id,
            "name": r.requirement.name,
            "framework": r.requirement.framework,
            "status": r.status.value,
            "article_ref": r.requirement.article_ref,
            "category": r.requirement.category,
        }
        if include_evidence:
            entry["evidence"] = r.evidence
        if include_recommendations:
            entry["recommendations"] = r.recommendations
        results_list.append(entry)

    return {
        "name": fw.name,
        "version": fw.version,
        "description": fw.description,
        "summary": {
            "total_controls": fw.summary.total_controls,
            "compliant": fw.summary.compliant,
            "partial": fw.summary.partial,
            "non_compliant": fw.summary.non_compliant,
            "not_applicable": fw.summary.not_applicable,
            "not_evaluated": fw.summary.not_evaluated,
            "compliance_rate": fw.summary.compliance_rate,
        },
        "results": results_list,
    }


def _json_default(obj: object) -> str:
    """JSON default serializer for non-standard types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)
