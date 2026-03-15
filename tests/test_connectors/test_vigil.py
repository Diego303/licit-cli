"""Tests for the vigil connector."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from licit.config.schema import ConnectorVigilConfig
from licit.connectors.base import Connector
from licit.connectors.vigil import VigilConnector
from licit.core.evidence import EvidenceBundle

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def vigil_project(tmp_path: Path) -> Path:
    """Create a project directory with vigil SARIF data."""
    shutil.copy(FIXTURES / "vigil_report.sarif", tmp_path / "results.sarif")
    (tmp_path / ".vigil.yaml").write_text("enabled: true\n", encoding="utf-8")
    return tmp_path


def make_connector(
    root: Path,
    enabled: bool = True,
    sarif_path: str | None = None,
    sbom_path: str | None = None,
    sarif_files: list[str] | None = None,
) -> VigilConnector:
    """Helper to build a VigilConnector."""
    cfg = ConnectorVigilConfig(
        enabled=enabled,
        sarif_path=sarif_path,
        sbom_path=sbom_path,
    )
    return VigilConnector(str(root), cfg, sarif_files=sarif_files)


class TestVigilConnectorProtocol:
    """Verify VigilConnector satisfies the Connector protocol."""

    def test_implements_protocol(self, tmp_path: Path) -> None:
        conn = make_connector(tmp_path)
        assert isinstance(conn, Connector)

    def test_name_property(self, tmp_path: Path) -> None:
        conn = make_connector(tmp_path)
        assert conn.name == "vigil"

    def test_enabled_property(self, tmp_path: Path) -> None:
        conn = make_connector(tmp_path, enabled=False)
        assert conn.enabled is False


class TestVigilSARIFReading:
    """Test reading SARIF files."""

    def test_reads_sarif_file(self, vigil_project: Path) -> None:
        conn = make_connector(vigil_project, sarif_path="results.sarif")
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert result.success is True  # files read, no errors
        assert result.files_read >= 1
        assert ev.security_findings_total == 3
        assert ev.security_findings_critical == 1  # 1 error
        assert ev.security_findings_high == 1      # 1 warning

    def test_reads_sarif_from_auto_detected_files(self, vigil_project: Path) -> None:
        conn = make_connector(
            vigil_project,
            sarif_files=["results.sarif"],
        )
        ev = EvidenceBundle()
        conn.collect(ev)

        assert ev.security_findings_total == 3

    def test_reads_sarif_directory(self, tmp_path: Path) -> None:
        sarif_dir = tmp_path / "sarif"
        sarif_dir.mkdir()
        shutil.copy(FIXTURES / "vigil_report.sarif", sarif_dir / "scan1.sarif")
        shutil.copy(FIXTURES / "vigil_report.sarif", sarif_dir / "scan2.sarif")

        conn = make_connector(tmp_path, sarif_path="sarif")
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert result.files_read == 2
        assert ev.security_findings_total == 6  # 3 per file × 2

    def test_missing_sarif_file(self, tmp_path: Path) -> None:
        conn = make_connector(tmp_path, sarif_path="nonexistent.sarif")
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert result.files_read == 0
        assert ev.security_findings_total == 0

    def test_malformed_sarif_json(self, tmp_path: Path) -> None:
        (tmp_path / "bad.sarif").write_text("not json at all", encoding="utf-8")
        conn = make_connector(tmp_path, sarif_path="bad.sarif")
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert len(result.errors) >= 1
        assert ev.security_findings_total == 0

    def test_sarif_not_object(self, tmp_path: Path) -> None:
        (tmp_path / "array.sarif").write_text("[1,2,3]", encoding="utf-8")
        conn = make_connector(tmp_path, sarif_path="array.sarif")
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert len(result.errors) >= 1

    def test_sarif_runs_not_list(self, tmp_path: Path) -> None:
        (tmp_path / "bad_runs.sarif").write_text(
            '{"runs": "not a list"}', encoding="utf-8",
        )
        conn = make_connector(tmp_path, sarif_path="bad_runs.sarif")
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert len(result.errors) >= 1

    def test_deduplicates_sarif_paths(self, vigil_project: Path) -> None:
        """Explicit path and auto-detected path for same file should not double-count."""
        conn = make_connector(
            vigil_project,
            sarif_path="results.sarif",
            sarif_files=["results.sarif"],
        )
        ev = EvidenceBundle()
        conn.collect(ev)

        # Should not double-count: explicit path takes priority
        assert ev.security_findings_total == 3


class TestVigilSARIFParsing:
    """Test SARIF finding extraction detail."""

    def test_finding_levels(self, vigil_project: Path) -> None:
        conn = make_connector(vigil_project, sarif_path="results.sarif")
        ev = EvidenceBundle()
        conn.collect(ev)

        # From fixture: 1 error, 1 warning, 1 note
        assert ev.security_findings_critical == 1
        assert ev.security_findings_high == 1

    def test_empty_results_array(self, tmp_path: Path) -> None:
        sarif = {
            "version": "2.1.0",
            "runs": [{"tool": {"driver": {"name": "vigil"}}, "results": []}],
        }
        (tmp_path / "empty.sarif").write_text(json.dumps(sarif), encoding="utf-8")
        conn = make_connector(tmp_path, sarif_path="empty.sarif")
        ev = EvidenceBundle()
        conn.collect(ev)

        assert ev.security_findings_total == 0

    def test_multiple_runs_in_one_sarif(self, tmp_path: Path) -> None:
        sarif = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "vigil"}},
                    "results": [{"ruleId": "V1", "level": "error", "message": {"text": "bad"}}],
                },
                {
                    "tool": {"driver": {"name": "other-tool"}},
                    "results": [{"ruleId": "O1", "level": "warning", "message": {"text": "hmm"}}],
                },
            ],
        }
        (tmp_path / "multi.sarif").write_text(json.dumps(sarif), encoding="utf-8")
        conn = make_connector(tmp_path, sarif_path="multi.sarif")
        ev = EvidenceBundle()
        conn.collect(ev)

        # Both runs are parsed regardless of tool name
        assert ev.security_findings_total == 2
        assert ev.security_findings_critical == 1
        assert ev.security_findings_high == 1

    def test_finding_without_location(self, tmp_path: Path) -> None:
        sarif = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "vigil"}},
                    "results": [
                        {"ruleId": "V1", "level": "error", "message": {"text": "no loc"}},
                    ],
                },
            ],
        }
        (tmp_path / "noloc.sarif").write_text(json.dumps(sarif), encoding="utf-8")
        conn = make_connector(tmp_path, sarif_path="noloc.sarif")
        ev = EvidenceBundle()
        conn.collect(ev)

        assert ev.security_findings_total == 1


class TestVigilSBOM:
    """Test SBOM reading."""

    def test_reads_sbom(self, tmp_path: Path) -> None:
        shutil.copy(FIXTURES / "sbom.json", tmp_path / "sbom.json")
        conn = make_connector(tmp_path, sbom_path="sbom.json")
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert result.files_read >= 1

    def test_missing_sbom(self, tmp_path: Path) -> None:
        conn = make_connector(tmp_path, sbom_path="nonexistent.json")
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert result.has_errors is False

    def test_malformed_sbom(self, tmp_path: Path) -> None:
        (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
        conn = make_connector(tmp_path, sbom_path="bad.json")
        ev = EvidenceBundle()
        result = conn.collect(ev)

        assert len(result.errors) >= 1


class TestVigilAvailability:
    """Test the available() check."""

    def test_available_with_sarif(self, vigil_project: Path) -> None:
        conn = make_connector(vigil_project, sarif_path="results.sarif")
        assert conn.available() is True

    def test_available_with_vigil_yaml(self, vigil_project: Path) -> None:
        conn = make_connector(vigil_project)
        assert conn.available() is True

    def test_available_with_auto_detected(self, vigil_project: Path) -> None:
        conn = make_connector(vigil_project, sarif_files=["results.sarif"])
        assert conn.available() is True

    def test_not_available(self, tmp_path: Path) -> None:
        conn = make_connector(tmp_path)
        assert conn.available() is False
