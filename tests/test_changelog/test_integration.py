"""Integration test: watcher → classifier → renderer full pipeline."""

import json
import subprocess
from pathlib import Path

import pytest

from licit.changelog.classifier import ChangeClassifier
from licit.changelog.renderer import ChangelogRenderer
from licit.changelog.watcher import ConfigWatcher
from licit.core.models import ChangeSeverity


@pytest.fixture
def multi_commit_project(tmp_path: Path) -> Path:
    """Git project with YAML + Markdown config changes across multiple commits."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "dev@test.com"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Dev"],
        cwd=tmp_path, capture_output=True, check=True,
    )

    # Commit 1: initial configs
    (tmp_path / "CLAUDE.md").write_text("# Rules\n\n- Be helpful\n- Write tests\n")
    (tmp_path / ".architect").mkdir()
    (tmp_path / ".architect" / "config.yaml").write_text(
        "llm:\n  model: claude-sonnet-4\n  provider: anthropic\n"
        "guardrails:\n  protected_files:\n    - '*.env'\n"
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial configs"],
        cwd=tmp_path, capture_output=True, check=True,
    )

    # Commit 2: change model (MAJOR) + update rules (MINOR)
    (tmp_path / "CLAUDE.md").write_text(
        "# Rules\n\n- Be helpful\n- Write tests\n- Use type hints\n"
    )
    (tmp_path / ".architect" / "config.yaml").write_text(
        "llm:\n  model: claude-opus-4\n  provider: anthropic\n"
        "guardrails:\n  protected_files:\n    - '*.env'\n    - credentials.json\n"
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Upgrade model and add rules"],
        cwd=tmp_path, capture_output=True, check=True,
    )

    return tmp_path


class TestFullPipeline:
    """End-to-end: watcher → classifier → renderer."""

    def test_full_pipeline_markdown(self, multi_commit_project: Path) -> None:
        """Full pipeline produces valid Markdown with correct severity counts."""
        root = str(multi_commit_project)

        # Step 1: Watch
        watcher = ConfigWatcher(root, ["CLAUDE.md", ".architect/config.yaml"])
        history = watcher.get_config_history()
        assert len(history) == 2  # Both files tracked

        # Step 2: Classify
        classifier = ChangeClassifier()
        all_changes = []
        for file_path, snapshots in history.items():
            for i in range(len(snapshots) - 1):
                changes = classifier.classify_changes(
                    old_content=snapshots[i + 1].content,
                    new_content=snapshots[i].content,
                    file_path=file_path,
                    commit_sha=snapshots[i].commit_sha,
                    timestamp=snapshots[i].timestamp,
                )
                all_changes.extend(changes)

        # Should have at least a model change (MAJOR) and rule edits (MINOR)
        assert len(all_changes) >= 2
        severities = {c.severity for c in all_changes}
        assert ChangeSeverity.MAJOR in severities  # model change

        # Step 3: Render Markdown
        renderer = ChangelogRenderer()
        md = renderer.render(all_changes, fmt="markdown")
        assert "# Agent Config Changelog" in md
        assert "CLAUDE.md" in md
        assert ".architect/config.yaml" in md
        assert "[MAJOR]" in md

    def test_full_pipeline_json(self, multi_commit_project: Path) -> None:
        """Full pipeline produces valid JSON with all expected fields."""
        root = str(multi_commit_project)

        watcher = ConfigWatcher(root, ["CLAUDE.md", ".architect/config.yaml"])
        history = watcher.get_config_history()

        classifier = ChangeClassifier()
        all_changes = []
        for file_path, snapshots in history.items():
            for i in range(len(snapshots) - 1):
                changes = classifier.classify_changes(
                    old_content=snapshots[i + 1].content,
                    new_content=snapshots[i].content,
                    file_path=file_path,
                    commit_sha=snapshots[i].commit_sha,
                    timestamp=snapshots[i].timestamp,
                )
                all_changes.extend(changes)

        renderer = ChangelogRenderer()
        output = renderer.render(all_changes, fmt="json")
        data = json.loads(output)

        assert "changes" in data
        assert len(data["changes"]) >= 2
        for entry in data["changes"]:
            assert "file_path" in entry
            assert "severity" in entry
            assert "commit_sha" in entry
            assert entry["severity"] in ("major", "minor", "patch")

    def test_no_changes_pipeline(self, multi_commit_project: Path) -> None:
        """Pipeline with file that has no changes produces empty changelog."""
        root = str(multi_commit_project)

        watcher = ConfigWatcher(root, ["nonexistent.md"])
        history = watcher.get_config_history()
        assert history == {}

        renderer = ChangelogRenderer()
        md = renderer.render([], fmt="markdown")
        assert "No changes detected" in md
