"""Tests for project auto-detection."""

import subprocess
from pathlib import Path

from licit.core.project import ProjectDetector


class TestProjectDetector:
    """Tests for ProjectDetector."""

    def test_detect_python_project(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "my-app"\n', encoding="utf-8"
        )
        (tmp_path / "tests").mkdir()

        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))

        assert ctx.name == "my-app"
        assert "python" in ctx.languages
        assert "pip" in ctx.package_managers
        assert ctx.test_framework == "pytest"

    def test_detect_javascript_project(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            '{"name": "my-js-app", "dependencies": {"react": "^18"}}',
            encoding="utf-8",
        )
        (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")

        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))

        assert ctx.name == "my-js-app"
        assert "javascript" in ctx.languages
        assert "typescript" in ctx.languages
        assert "react" in ctx.frameworks

    def test_detect_go_project(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("module example.com/app\n", encoding="utf-8")

        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))

        assert "go" in ctx.languages
        assert "go-modules" in ctx.package_managers

    def test_detect_agent_configs(self, tmp_path: Path) -> None:
        (tmp_path / "CLAUDE.md").write_text("# Agent instructions\n", encoding="utf-8")
        (tmp_path / ".cursorrules").write_text("rules here\n", encoding="utf-8")

        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))

        assert len(ctx.agent_configs) == 2
        types = {c.agent_type for c in ctx.agent_configs}
        assert "claude-code" in types
        assert "cursor" in types

    def test_detect_architect(self, tmp_path: Path) -> None:
        (tmp_path / ".architect").mkdir()
        (tmp_path / ".architect" / "config.yaml").write_text(
            "llm:\n  model: claude-sonnet-4\n", encoding="utf-8"
        )

        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))

        assert ctx.has_architect is True
        assert ctx.architect_config_path == ".architect/config.yaml"

    def test_detect_cicd_github_actions(self, tmp_path: Path) -> None:
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("name: CI\n", encoding="utf-8")

        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))

        assert ctx.cicd.platform == "github-actions"

    def test_detect_security_tools(self, tmp_path: Path) -> None:
        (tmp_path / ".vigil.yaml").write_text("---\n", encoding="utf-8")
        (tmp_path / ".semgrep.yml").write_text("rules: []\n", encoding="utf-8")

        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))

        assert ctx.security.has_vigil is True
        assert ctx.security.vigil_config_path == ".vigil.yaml"
        assert ctx.security.has_semgrep is True

    def test_detect_git_info(self, tmp_path: Path) -> None:
        # Init git repo with a commit
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        (tmp_path / "file.txt").write_text("hello\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path, capture_output=True, check=True,
        )

        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))

        assert ctx.git_initialized is True
        assert ctx.total_commits >= 1
        assert ctx.total_contributors >= 1

    def test_detect_no_git(self, tmp_path: Path) -> None:
        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))

        assert ctx.git_initialized is False
        assert ctx.total_commits == 0

    def test_detect_frameworks_python(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "api"\ndependencies = ["fastapi"]\n',
            encoding="utf-8",
        )

        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))

        assert "fastapi" in ctx.frameworks

    def test_detect_empty_project(self, tmp_path: Path) -> None:
        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))

        assert ctx.name == tmp_path.name
        assert ctx.languages == []
        assert ctx.agent_configs == []
        assert ctx.cicd.platform == "none"

    def test_detect_name_from_package_json_when_no_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            '{"name": "frontend-app"}', encoding="utf-8"
        )

        detector = ProjectDetector()
        ctx = detector.detect(str(tmp_path))

        assert ctx.name == "frontend-app"
