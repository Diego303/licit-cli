"""Tests for CLI commands."""

import os
import subprocess
from pathlib import Path

from click.testing import CliRunner

from licit.cli import main


class TestCLIHelp:
    """Tests for CLI help output."""

    def test_main_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "licit" in result.output
        assert "init" in result.output
        assert "trace" in result.output
        assert "status" in result.output

    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_init_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["init", "--help"])
        assert result.exit_code == 0
        assert "Initialize" in result.output
        assert "--framework" in result.output

    def test_trace_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["trace", "--help"])
        assert result.exit_code == 0
        assert "--since" in result.output
        assert "--stats" in result.output

    def test_all_commands_registered(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        expected_commands = [
            "init", "trace", "changelog", "fria", "annex-iv",
            "report", "gaps", "verify", "status", "connect",
        ]
        for cmd in expected_commands:
            assert cmd in result.output, f"Command '{cmd}' not in help output"


class TestInitCommand:
    """Tests for the init command."""

    def test_init_creates_config_and_dir(self, tmp_path: Path) -> None:
        # Set up a basic project with git
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "T"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        (tmp_path / "README.md").write_text("# Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path, capture_output=True, check=True,
        )

        original = os.getcwd()
        try:
            os.chdir(tmp_path)
            runner = CliRunner()
            result = runner.invoke(main, ["init"], catch_exceptions=False)
            assert result.exit_code == 0
            assert (tmp_path / ".licit.yaml").exists()
            assert (tmp_path / ".licit").is_dir()
        finally:
            os.chdir(original)

    def test_init_with_framework_flag(self, tmp_path: Path) -> None:
        import yaml

        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "T"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        (tmp_path / "README.md").write_text("# Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path, capture_output=True, check=True,
        )

        original = os.getcwd()
        try:
            os.chdir(tmp_path)
            runner = CliRunner()
            result = runner.invoke(
                main, ["init", "--framework", "eu-ai-act"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            config_data = yaml.safe_load(
                (tmp_path / ".licit.yaml").read_text(encoding="utf-8")
            )
            assert config_data["frameworks"]["eu_ai_act"] is True
            assert config_data["frameworks"]["owasp_agentic"] is False
        finally:
            os.chdir(original)

    def test_init_detects_python(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "myapp"\n', encoding="utf-8"
        )
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "T"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        (tmp_path / "file.txt").write_text("x\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path, capture_output=True, check=True,
        )

        original = os.getcwd()
        try:
            os.chdir(tmp_path)
            runner = CliRunner()
            result = runner.invoke(main, ["init"], catch_exceptions=False)
            assert result.exit_code == 0
            assert "python" in result.output.lower() or "myapp" in result.output
        finally:
            os.chdir(original)


class TestStatusCommand:
    """Tests for the status command."""

    def test_status_without_init(self, tmp_path: Path) -> None:
        original = os.getcwd()
        try:
            os.chdir(tmp_path)
            runner = CliRunner()
            result = runner.invoke(main, ["status"], catch_exceptions=False)
            assert result.exit_code == 0
            assert "licit Status" in result.output
        finally:
            os.chdir(original)

    def test_status_shows_frameworks(self, tmp_path: Path) -> None:
        original = os.getcwd()
        try:
            os.chdir(tmp_path)
            runner = CliRunner()
            result = runner.invoke(main, ["status"], catch_exceptions=False)
            assert result.exit_code == 0
            assert "EU AI Act" in result.output
            assert "OWASP" in result.output
        finally:
            os.chdir(original)

    def test_status_shows_data_sources(self, tmp_path: Path) -> None:
        original = os.getcwd()
        try:
            os.chdir(tmp_path)
            runner = CliRunner()
            result = runner.invoke(main, ["status"], catch_exceptions=False)
            assert result.exit_code == 0
            assert "Data Sources" in result.output
            assert "Connectors" in result.output
        finally:
            os.chdir(original)


class TestConnectCommand:
    """Tests for the connect command."""

    def test_connect_enable_architect(self, tmp_path: Path) -> None:
        import yaml

        # Create a config file first
        config_file = tmp_path / ".licit.yaml"
        config_file.write_text(
            yaml.dump({"connectors": {"architect": {"enabled": False}}}),
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(
            main, ["--config", str(config_file), "connect", "architect", "--enable"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "enabled" in result.output

    def test_connect_disable_vigil(self, tmp_path: Path) -> None:
        import yaml

        config_file = tmp_path / ".licit.yaml"
        config_file.write_text(yaml.dump({}), encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            main, ["--config", str(config_file), "connect", "vigil", "--disable"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "disabled" in result.output
