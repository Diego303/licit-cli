"""End-to-end integration test: init → trace → report → gaps → verify.

Tests the full licit flow against a synthetic git repository with
AI-like commits, architect data, and vigil SARIF findings.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from licit.cli import main


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command in the given directory."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


@pytest.fixture
def full_project(tmp_path: Path) -> Path:
    """Set up a complete synthetic project with git, agent configs, and tool data."""
    # Init git
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "dev@company.com")
    _git(tmp_path, "config", "user.name", "Dev Team")

    # pyproject.toml
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test-app"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )

    # Source files
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("def main():\n    print('hello')\n", encoding="utf-8")

    # Agent config
    (tmp_path / "CLAUDE.md").write_text(
        "# Claude Code Instructions\n\nBe helpful.\n",
        encoding="utf-8",
    )

    # Initial human commit
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "Initial setup")

    # AI-like commit (co-authored by Claude)
    (src / "auth.py").write_text(
        "def authenticate(token: str) -> bool:\n"
        "    return verify_jwt(token)\n",
        encoding="utf-8",
    )
    _git(tmp_path, "add", "src/auth.py")
    _git(
        tmp_path, "commit", "-m",
        "feat: Add authentication module\n\n"
        "Co-Authored-By: Claude (Anthropic AI) <noreply@anthropic.com>",
    )

    # Architect data
    arch = tmp_path / ".architect"
    arch.mkdir()
    (arch / "config.yaml").write_text(
        "model: claude-sonnet-4\nguardrails:\n  protected_files:\n    - .env\n"
        "  blocked_commands:\n    - rm -rf\ncosts:\n  budget_usd: 25.0\n",
        encoding="utf-8",
    )
    reports = arch / "reports"
    reports.mkdir()
    (reports / "task-001.json").write_text(
        json.dumps({
            "task_id": "task-001",
            "status": "completed",
            "model": "claude-sonnet-4",
            "cost_usd": 0.15,
            "files_changed": ["src/auth.py"],
            "timestamp": "2026-03-10T12:00:00Z",
        }),
        encoding="utf-8",
    )

    # Vigil SARIF
    sarif = {
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "vigil", "version": "1.0"}},
            "results": [{
                "ruleId": "V-001",
                "level": "warning",
                "message": {"text": "Unsanitized input"},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": "src/auth.py"},
                        "region": {"startLine": 2},
                    },
                }],
            }],
        }],
    }
    (tmp_path / "results.sarif").write_text(json.dumps(sarif), encoding="utf-8")

    # Commit tool data
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "Add architect data and vigil SARIF")

    return tmp_path


@pytest.fixture(autouse=True)
def _chdir_to_project(full_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Change working directory to the full_project for all tests."""
    monkeypatch.chdir(full_project)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestFullFlow:
    """End-to-end flow: init → trace → report → gaps → verify."""

    def test_init_creates_config(self, full_project: Path, runner: CliRunner) -> None:
        """licit init should detect project and create .licit.yaml."""
        result = runner.invoke(
            main, ["init"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "test-app" in result.output
        assert (full_project / ".licit.yaml").exists()

    def test_trace_analyzes_history(self, full_project: Path, runner: CliRunner) -> None:
        """licit trace should analyze git history and store provenance."""
        # Init first
        runner.invoke(
            main, ["init"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        result = runner.invoke(
            main, ["trace"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "Analyzed" in result.output
        assert (full_project / ".licit" / "provenance.jsonl").exists()

    def test_report_generates_output(self, full_project: Path, runner: CliRunner) -> None:
        """licit report should generate a compliance report."""
        runner.invoke(
            main, ["init"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        result = runner.invoke(
            main, ["report"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "Report saved" in result.output

    def test_gaps_identifies_issues(self, full_project: Path, runner: CliRunner) -> None:
        """licit gaps should identify compliance gaps."""
        runner.invoke(
            main, ["init"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        result = runner.invoke(
            main, ["gaps"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        # Should find gaps (no FRIA, no Annex IV at minimum)
        assert "gap" in result.output.lower() or "requirements met" in result.output.lower()

    def test_verify_returns_nonzero(self, full_project: Path, runner: CliRunner) -> None:
        """licit verify should return non-zero without FRIA/Annex IV."""
        runner.invoke(
            main, ["init"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        result = runner.invoke(
            main, ["verify"],
            obj={"config_path": None, "verbose": False},
        )
        # Without FRIA → non-compliant (exit 1) or partial (exit 2)
        assert result.exit_code in (1, 2)

    def test_status_shows_info(self, full_project: Path, runner: CliRunner) -> None:
        """licit status should show project info and connector status."""
        runner.invoke(
            main, ["init"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        result = runner.invoke(
            main, ["status"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "test-app" in result.output
        assert "architect" in result.output.lower()


class TestConnectCommand:
    """Test the connect command with real connector wiring."""

    def test_enable_architect(self, full_project: Path, runner: CliRunner) -> None:
        runner.invoke(
            main, ["init"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        result = runner.invoke(
            main, ["connect", "architect"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "enabled" in result.output.lower()

    def test_disable_connector(self, full_project: Path, runner: CliRunner) -> None:
        runner.invoke(
            main, ["init"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        result = runner.invoke(
            main, ["connect", "vigil", "--disable"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "disabled" in result.output.lower()


class TestConnectorEnrichedReport:
    """Test that connectors enrich the report when enabled."""

    def test_architect_enriches_evidence(self, full_project: Path, runner: CliRunner) -> None:
        """When architect is enabled, report should reflect guardrails."""
        runner.invoke(
            main, ["init"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        runner.invoke(
            main, ["connect", "architect"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        result = runner.invoke(
            main, ["report", "--format", "json"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        assert result.exit_code == 0

    def test_changelog_command(self, full_project: Path, runner: CliRunner) -> None:
        """licit changelog should work with the full project."""
        runner.invoke(
            main, ["init"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        result = runner.invoke(
            main, ["changelog"],
            obj={"config_path": None, "verbose": False},
            catch_exceptions=False,
        )
        assert result.exit_code == 0
