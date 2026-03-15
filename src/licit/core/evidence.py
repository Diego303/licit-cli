"""Collects evidence from all available sources for compliance evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import structlog

from licit.config.schema import LicitConfig
from licit.connectors.architect import ArchitectConnector
from licit.connectors.base import ConnectorResult
from licit.connectors.vigil import VigilConnector
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

    def __init__(
        self,
        root_dir: str,
        context: ProjectContext,
        config: LicitConfig | None = None,
    ) -> None:
        self.root = Path(root_dir)
        self.context = context
        self.config = config
        self._connector_results: list[ConnectorResult] = []

    @property
    def connector_results(self) -> list[ConnectorResult]:
        """Results from the last collect() call's connector runs."""
        return list(self._connector_results)

    def collect(self) -> EvidenceBundle:
        """Collect all available evidence."""
        ev = EvidenceBundle()
        self._connector_results = []

        # Licit's own data
        self._collect_licit_data(ev)

        # Project-level detection (CI/CD heuristics)
        self._collect_project_evidence(ev)

        # Connectors (architect, vigil) — use formal connectors if config
        # available, fall back to inline detection for backwards compatibility
        self._run_connectors(ev)

        logger.info(
            "evidence_collected",
            has_provenance=ev.has_provenance,
            has_fria=ev.has_fria,
            has_guardrails=ev.has_guardrails,
            has_audit_trail=ev.has_audit_trail,
            connectors_run=len(self._connector_results),
        )
        return ev

    def _collect_licit_data(self, ev: EvidenceBundle) -> None:
        """Collect evidence from licit's own generated data."""
        licit_dir = self.root / ".licit"

        # Provenance store
        provenance_store = licit_dir / "provenance.jsonl"
        if provenance_store.exists():
            ev.has_provenance = True
            from licit.provenance.store import ProvenanceStore

            store = ProvenanceStore(str(provenance_store))
            ev.provenance_stats = store.get_stats()

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
        # CI/CD with GitHub Actions likely has PR review process
        if self.context.cicd.platform == "github-actions":
            ev.has_human_review_gate = True

    def _run_connectors(self, ev: EvidenceBundle) -> None:
        """Run enabled connectors or fall back to inline detection."""
        architect_ran = self._run_architect_connector(ev)
        vigil_ran = self._run_vigil_connector(ev)

        # Backwards compatibility: if no formal config was provided,
        # use inline detection methods from the project context
        if not architect_ran:
            self._collect_architect_evidence_inline(ev)
        if not vigil_ran:
            self._collect_vigil_evidence_inline(ev)

    def _run_architect_connector(self, ev: EvidenceBundle) -> bool:
        """Run the architect connector if config is available and enabled."""
        if self.config is None:
            return False

        connector = ArchitectConnector(
            str(self.root),
            self.config.connectors.architect,
        )
        if not connector.enabled:
            return False

        result = connector.collect(ev)
        self._connector_results.append(result)
        return True

    def _run_vigil_connector(self, ev: EvidenceBundle) -> bool:
        """Run the vigil connector if config is available and enabled."""
        if self.config is None:
            return False

        connector = VigilConnector(
            str(self.root),
            self.config.connectors.vigil,
            sarif_files=self.context.security.sarif_files,
        )
        if not connector.enabled:
            return False

        result = connector.collect(ev)
        self._connector_results.append(result)
        return True

    # -- Backwards-compatible inline collectors (no config needed) --

    def _collect_architect_evidence_inline(self, ev: EvidenceBundle) -> None:
        """Collect architect evidence without formal connector config.

        Constructs a temporary ArchitectConnector with auto-detected paths
        to avoid duplicating the parsing logic.
        """
        from licit.config.schema import ConnectorArchitectConfig

        inline_config = ConnectorArchitectConfig(
            enabled=True,
            reports_dir=".architect/reports",
            config_path=self.context.architect_config_path,
        )
        connector = ArchitectConnector(str(self.root), inline_config)
        connector.collect(ev)

    def _collect_vigil_evidence_inline(self, ev: EvidenceBundle) -> None:
        """Collect SARIF evidence without formal connector config.

        Constructs a temporary VigilConnector with auto-detected SARIF paths
        to avoid duplicating the parsing logic.
        """
        from licit.config.schema import ConnectorVigilConfig

        inline_config = ConnectorVigilConfig(enabled=True)
        connector = VigilConnector(
            str(self.root),
            inline_config,
            sarif_files=self.context.security.sarif_files,
        )
        connector.collect(ev)
