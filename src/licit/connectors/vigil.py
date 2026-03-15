"""Vigil connector — reads SARIF security findings and SBOM data.

vigil is a security scanner for AI-generated code that outputs SARIF
(Static Analysis Results Interchange Format) files. This connector reads
those files and enriches the EvidenceBundle with security findings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from licit.config.schema import ConnectorVigilConfig
from licit.connectors.base import ConnectorResult

if TYPE_CHECKING:
    from licit.core.evidence import EvidenceBundle

logger = structlog.get_logger()


# Standard SARIF severity levels
SARIF_LEVEL_CRITICAL = "error"
SARIF_LEVEL_HIGH = "warning"
SARIF_LEVEL_MEDIUM = "note"
SARIF_LEVEL_LOW = "none"


@dataclass
class SARIFFinding:
    """A single finding from a SARIF file."""

    rule_id: str
    level: str
    message: str
    file_path: str | None = None
    start_line: int | None = None
    tool_name: str = ""


@dataclass
class SARIFSummary:
    """Summary of findings from one SARIF file."""

    tool_name: str
    total: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    findings: list[SARIFFinding] = field(default_factory=list)


class VigilConnector:
    """Reads vigil SARIF files and SBOM data to enrich evidence."""

    name = "vigil"

    def __init__(
        self,
        root_dir: str,
        config: ConnectorVigilConfig,
        sarif_files: list[str] | None = None,
    ) -> None:
        self.root = Path(root_dir)
        self.config = config
        self._sarif_files = sarif_files or []

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def available(self) -> bool:
        """Check if any SARIF files or vigil config exist on disk."""
        if self.config.sarif_path and (self.root / self.config.sarif_path).exists():
            return True
        if (self.root / ".vigil.yaml").exists():
            return True
        return any((self.root / f).exists() for f in self._sarif_files)

    def collect(self, evidence: EvidenceBundle) -> ConnectorResult:
        """Read all SARIF files and enrich the evidence bundle."""
        result = ConnectorResult(connector_name=self.name)

        sarif_paths = self._resolve_sarif_paths()
        for sarif_path in sarif_paths:
            self._read_sarif(sarif_path, evidence, result)

        if self.config.sbom_path:
            self._read_sbom(result)

        logger.info(
            "vigil_connector_collected",
            sarif_files=len(sarif_paths),
            total_findings=evidence.security_findings_total,
            errors=len(result.errors),
        )
        return result

    def _resolve_sarif_paths(self) -> list[Path]:
        """Build list of SARIF file paths to read."""
        paths: list[Path] = []

        # Explicit config path takes priority
        if self.config.sarif_path:
            explicit = self.root / self.config.sarif_path
            if explicit.is_file():
                paths.append(explicit)
            elif explicit.is_dir():
                paths.extend(sorted(explicit.glob("*.sarif")))

        # Auto-detected SARIF files from project context
        for rel_path in self._sarif_files:
            full = self.root / rel_path
            if full.exists() and full not in paths:
                paths.append(full)

        return paths

    def _read_sarif(
        self,
        sarif_path: Path,
        evidence: EvidenceBundle,
        result: ConnectorResult,
    ) -> None:
        """Parse a single SARIF file and update evidence."""
        try:
            data = json.loads(sarif_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            result.errors.append(f"{sarif_path.name}: {exc}")
            logger.debug("sarif_read_error", path=str(sarif_path), error=str(exc))
            return

        if not isinstance(data, dict):
            result.errors.append(f"{sarif_path.name}: not a JSON object")
            return

        runs = data.get("runs", [])
        if not isinstance(runs, list):
            result.errors.append(f"{sarif_path.name}: 'runs' is not a list")
            return

        result.files_read += 1

        for run in runs:
            if not isinstance(run, dict):
                continue
            summary = self._parse_run(run)
            evidence.security_findings_total += summary.total
            evidence.security_findings_critical += summary.critical
            evidence.security_findings_high += summary.high

    def _parse_run(self, run: dict[str, object]) -> SARIFSummary:
        """Parse a single SARIF run and return summary."""
        tool_name = self._extract_tool_name(run)
        summary = SARIFSummary(tool_name=tool_name)

        results = run.get("results", [])
        if not isinstance(results, list):
            return summary

        for item in results:
            if not isinstance(item, dict):
                continue

            finding = self._parse_finding(item, tool_name)
            summary.findings.append(finding)
            summary.total += 1

            if finding.level == SARIF_LEVEL_CRITICAL:
                summary.critical += 1
            elif finding.level == SARIF_LEVEL_HIGH:
                summary.high += 1
            elif finding.level == SARIF_LEVEL_MEDIUM:
                summary.medium += 1
            else:
                summary.low += 1

        return summary

    @staticmethod
    def _extract_tool_name(run: dict[str, object]) -> str:
        """Extract tool name from a SARIF run object."""
        tool_obj = run.get("tool", {})
        driver = tool_obj.get("driver", {}) if isinstance(tool_obj, dict) else {}
        name = driver.get("name", "") if isinstance(driver, dict) else ""
        return name if isinstance(name, str) else ""

    @staticmethod
    def _parse_finding(item: dict[str, object], tool_name: str) -> SARIFFinding:
        """Parse a single SARIF result into a SARIFFinding."""
        rule_id = item.get("ruleId", "unknown")
        if not isinstance(rule_id, str):
            rule_id = "unknown"

        level = item.get("level", "warning")
        if not isinstance(level, str):
            level = "warning"

        message_obj = item.get("message", {})
        message = (
            message_obj.get("text", "") if isinstance(message_obj, dict) else ""
        )
        if not isinstance(message, str):
            message = ""

        file_path, start_line = VigilConnector._extract_location(item)

        return SARIFFinding(
            rule_id=rule_id,
            level=level,
            message=message,
            file_path=file_path,
            start_line=start_line,
            tool_name=tool_name,
        )

    @staticmethod
    def _extract_location(item: dict[str, object]) -> tuple[str | None, int | None]:
        """Extract file path and start line from SARIF locations array."""
        locations = item.get("locations", [])
        if not isinstance(locations, list) or not locations:
            return None, None

        loc = locations[0]
        if not isinstance(loc, dict):
            return None, None

        phys = loc.get("physicalLocation", {})
        if not isinstance(phys, dict):
            return None, None

        file_path: str | None = None
        artifact = phys.get("artifactLocation", {})
        if isinstance(artifact, dict):
            uri = artifact.get("uri")
            if isinstance(uri, str):
                file_path = uri

        start_line: int | None = None
        region = phys.get("region", {})
        if isinstance(region, dict):
            sl = region.get("startLine")
            if isinstance(sl, int):
                start_line = sl

        return file_path, start_line

    def _read_sbom(self, result: ConnectorResult) -> None:
        """Read SBOM (Software Bill of Materials) file if configured.

        V0: validates the file and counts it as a read. In V1, SBOM data
        will feed into OWASP ASI03 (Supply Chain Vulnerabilities) evaluation
        once EvidenceBundle gets supply-chain fields.
        """
        if not self.config.sbom_path:
            return

        sbom_path = self.root / self.config.sbom_path
        if not sbom_path.exists():
            return

        try:
            data = json.loads(sbom_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                result.errors.append("SBOM: not a JSON object")
                return

            result.files_read += 1
            components = data.get("components", [])
            logger.debug(
                "sbom_read",
                format=data.get("bomFormat", "unknown"),
                components=len(components) if isinstance(components, list) else 0,
            )

        except (json.JSONDecodeError, OSError) as exc:
            result.errors.append(f"SBOM: {exc}")
            logger.debug("sbom_read_error", error=str(exc))
