"""Collects evidence from all available sources for compliance evaluation."""

import json
from dataclasses import dataclass, field
from pathlib import Path

import structlog
import yaml

from licit.core.project import ProjectContext

logger = structlog.get_logger()


@dataclass
class EvidenceBundle:
    """All evidence collected for compliance evaluation."""

    # Provenance
    has_provenance: bool = False
    provenance_stats: dict[str, object] = field(default_factory=dict)

    # Changelog
    has_changelog: bool = False
    changelog_entry_count: int = 0

    # FRIA
    has_fria: bool = False
    fria_path: str | None = None

    # Annex IV
    has_annex_iv: bool = False
    annex_iv_path: str | None = None

    # Guardrails (from architect or detected configs)
    has_guardrails: bool = False
    guardrail_count: int = 0

    # Quality gates
    has_quality_gates: bool = False
    quality_gate_count: int = 0

    # Budget limits
    has_budget_limits: bool = False

    # Audit trail
    has_audit_trail: bool = False
    audit_entry_count: int = 0

    # OTel
    has_otel: bool = False

    # Human review
    has_human_review_gate: bool = False

    # Dry-run capability
    has_dry_run: bool = False

    # Rollback capability
    has_rollback: bool = False

    # Requirements traceability (from intake)
    has_requirements_traceability: bool = False

    # Security findings (from vigil/SARIF)
    security_findings_total: int = 0
    security_findings_critical: int = 0
    security_findings_high: int = 0


class EvidenceCollector:
    """Collects evidence from project context, connectors, and licit's own data."""

    def __init__(self, root_dir: str, context: ProjectContext) -> None:
        self.root = Path(root_dir)
        self.context = context

    def collect(self) -> EvidenceBundle:
        """Collect all available evidence."""
        ev = EvidenceBundle()

        self._collect_licit_data(ev)
        self._collect_project_evidence(ev)
        self._collect_architect_evidence(ev)
        self._collect_vigil_evidence(ev)

        logger.info(
            "evidence_collected",
            has_provenance=ev.has_provenance,
            has_fria=ev.has_fria,
            has_guardrails=ev.has_guardrails,
            has_audit_trail=ev.has_audit_trail,
        )
        return ev

    def _collect_licit_data(self, ev: EvidenceBundle) -> None:
        """Collect evidence from licit's own generated data."""
        licit_dir = self.root / ".licit"

        # Provenance store
        provenance_store = licit_dir / "provenance.jsonl"
        if provenance_store.exists():
            ev.has_provenance = True
            try:
                from licit.provenance.store import ProvenanceStore  # type: ignore[import-not-found]

                store = ProvenanceStore(str(provenance_store))
                ev.provenance_stats = store.get_stats()
            except ImportError:
                logger.debug("provenance_module_not_available")

        # Changelog
        changelog = licit_dir / "changelog.md"
        if changelog.exists():
            ev.has_changelog = True
            content = changelog.read_text(encoding="utf-8")
            ev.changelog_entry_count = sum(
                1 for line in content.splitlines() if line.startswith("## ")
            )

        # FRIA
        fria_data = licit_dir / "fria-data.json"
        if fria_data.exists():
            ev.has_fria = True
            ev.fria_path = str(fria_data.relative_to(self.root))

        # Annex IV
        annex_iv = licit_dir / "annex-iv.md"
        if annex_iv.exists():
            ev.has_annex_iv = True
            ev.annex_iv_path = str(annex_iv.relative_to(self.root))

    def _collect_project_evidence(self, ev: EvidenceBundle) -> None:
        """Collect evidence from project configuration files."""
        if self.context.architect_config_path:
            self._parse_architect_config(ev)

        # CI/CD with GitHub Actions likely has PR review process
        if self.context.cicd.platform == "github-actions":
            ev.has_human_review_gate = True

    def _parse_architect_config(self, ev: EvidenceBundle) -> None:
        """Extract evidence from architect config YAML."""
        try:
            config_path = self.root / (self.context.architect_config_path or "")
            if not config_path.exists():
                return
            data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return

            guardrails = data.get("guardrails", {})
            if isinstance(guardrails, dict) and guardrails:
                ev.has_guardrails = True
                ev.guardrail_count = (
                    len(guardrails.get("protected_files", []))
                    + len(guardrails.get("blocked_commands", []))
                    + len(guardrails.get("code_rules", []))
                )
                quality_gates = guardrails.get("quality_gates")
                if quality_gates:
                    ev.has_quality_gates = True
                    ev.quality_gate_count = (
                        len(quality_gates) if isinstance(quality_gates, list) else 0
                    )

            costs = data.get("costs", {})
            if isinstance(costs, dict) and costs.get("budget_usd"):
                ev.has_budget_limits = True

            if data.get("dry_run") is not False:
                ev.has_dry_run = True
            if data.get("rollback") is not False:
                ev.has_rollback = True

        except (yaml.YAMLError, OSError, KeyError, TypeError, ValueError) as exc:
            logger.debug("architect_config_parse_error", error=str(exc))

    def _collect_architect_evidence(self, ev: EvidenceBundle) -> None:
        """Collect evidence from architect reports (if available)."""
        reports_dir = self.root / ".architect" / "reports"
        if reports_dir.exists():
            reports = list(reports_dir.glob("*.json"))
            if reports:
                ev.has_audit_trail = True
                ev.audit_entry_count = len(reports)

    def _collect_vigil_evidence(self, ev: EvidenceBundle) -> None:
        """Collect evidence from vigil SARIF files (if available)."""
        for sarif_path in self.context.security.sarif_files:
            try:
                data = json.loads((self.root / sarif_path).read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    continue
                runs = data.get("runs", [])
                if not isinstance(runs, list):
                    continue
                for run in runs:
                    if not isinstance(run, dict):
                        continue
                    tool_name = run.get("tool", {}).get("driver", {}).get("name", "")
                    if not isinstance(tool_name, str) or "vigil" not in tool_name.lower():
                        continue
                    results = run.get("results", [])
                    if not isinstance(results, list):
                        continue
                    ev.security_findings_total += len(results)
                    for r in results:
                        if not isinstance(r, dict):
                            continue
                        level = r.get("level", "")
                        if level == "error":
                            ev.security_findings_critical += 1
                        elif level == "warning":
                            ev.security_findings_high += 1
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("sarif_parse_error", path=sarif_path, error=str(exc))
