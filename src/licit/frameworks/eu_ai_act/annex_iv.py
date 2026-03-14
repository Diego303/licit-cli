"""Annex IV Technical Documentation generator (EU AI Act).

Auto-populates technical documentation from project metadata including
pyproject.toml, package.json, CI/CD configs, agent configs, and test frameworks.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader

from licit.core.evidence import EvidenceBundle
from licit.core.project import ProjectContext

logger = structlog.get_logger()


class AnnexIVGenerator:
    """Generates Annex IV technical documentation from project metadata."""

    def __init__(self, context: ProjectContext, evidence: EvidenceBundle) -> None:
        self.context = context
        self.evidence = evidence

    def generate(
        self,
        output_path: str,
        organization: str,
        product_name: str,
    ) -> None:
        """Generate Annex IV documentation and write to output_path."""
        data = self._collect_data(organization, product_name)

        template_dir = Path(__file__).parent / "templates"
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,
            keep_trailing_newline=True,
        )
        template = env.get_template("annex_iv_template.md.j2")
        report = template.render(**data)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(report, encoding="utf-8")
        logger.info("annex_iv_generated", path=output_path)

    def _collect_data(self, organization: str, product_name: str) -> dict[str, object]:
        """Collect all data needed for the Annex IV template."""
        ctx = self.context
        ev = self.evidence
        now = datetime.now(tz=UTC)

        # AI tools in use
        agent_types = sorted({c.agent_type for c in ctx.agent_configs})

        # Security tools
        security_tools: list[str] = []
        if ctx.security.has_vigil:
            security_tools.append("vigil")
        if ctx.security.has_semgrep:
            security_tools.append("Semgrep")
        if ctx.security.has_snyk:
            security_tools.append("Snyk")
        if ctx.security.has_codeql:
            security_tools.append("CodeQL")
        if ctx.security.has_trivy:
            security_tools.append("Trivy")

        # Provenance stats
        ai_pct_raw = ev.provenance_stats.get("ai_percentage", 0)
        ai_pct = float(ai_pct_raw) if isinstance(ai_pct_raw, (int, float)) else 0.0

        return {
            "organization": organization,
            "product_name": product_name,
            "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
            "project_name": ctx.name,
            "languages": ctx.languages,
            "frameworks": ctx.frameworks,
            "package_managers": ctx.package_managers,
            "agent_configs": ctx.agent_configs,
            "agent_types": agent_types,
            "has_architect": ctx.has_architect,
            "cicd_platform": ctx.cicd.platform,
            "cicd_config_path": ctx.cicd.config_path,
            "test_framework": ctx.test_framework,
            "test_dirs": ctx.test_dirs,
            "security_tools": security_tools,
            "git_initialized": ctx.git_initialized,
            "total_commits": ctx.total_commits,
            "total_contributors": ctx.total_contributors,
            "has_provenance": ev.has_provenance,
            "ai_percentage": ai_pct,
            "has_audit_trail": ev.has_audit_trail,
            "audit_entry_count": ev.audit_entry_count,
            "has_guardrails": ev.has_guardrails,
            "guardrail_count": ev.guardrail_count,
            "has_quality_gates": ev.has_quality_gates,
            "quality_gate_count": ev.quality_gate_count,
            "has_budget_limits": ev.has_budget_limits,
            "has_human_review_gate": ev.has_human_review_gate,
            "has_fria": ev.has_fria,
            "has_changelog": ev.has_changelog,
        }
