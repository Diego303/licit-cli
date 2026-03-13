"""Tests for licit.changelog.watcher — config file detection and git history."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from licit.changelog.watcher import ConfigSnapshot, ConfigWatcher


@pytest.fixture
def changelog_git_project(tmp_path: Path) -> Path:
    """Create a git project with agent config file history."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Tester"],
        cwd=tmp_path, capture_output=True, check=True,
    )

    # Commit 1: initial CLAUDE.md
    (tmp_path / "CLAUDE.md").write_text("# Instructions\n\nBe helpful.\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add CLAUDE.md"],
        cwd=tmp_path, capture_output=True, check=True,
    )

    # Commit 2: update CLAUDE.md
    (tmp_path / "CLAUDE.md").write_text("# Instructions\n\nBe helpful and thorough.\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Update CLAUDE.md"],
        cwd=tmp_path, capture_output=True, check=True,
    )

    return tmp_path


class TestConfigWatcher:
    """Test ConfigWatcher git history retrieval."""

    def test_get_config_history_returns_snapshots(
        self, changelog_git_project: Path
    ) -> None:
        watcher = ConfigWatcher(str(changelog_git_project), ["CLAUDE.md"])
        history = watcher.get_config_history()
        assert "CLAUDE.md" in history
        assert len(history["CLAUDE.md"]) == 2

    def test_snapshots_are_newest_first(self, changelog_git_project: Path) -> None:
        watcher = ConfigWatcher(str(changelog_git_project), ["CLAUDE.md"])
        history = watcher.get_config_history()
        snapshots = history["CLAUDE.md"]
        assert snapshots[0].timestamp >= snapshots[1].timestamp

    def test_snapshot_has_correct_content(self, changelog_git_project: Path) -> None:
        watcher = ConfigWatcher(str(changelog_git_project), ["CLAUDE.md"])
        history = watcher.get_config_history()
        newest = history["CLAUDE.md"][0]
        assert "thorough" in newest.content
        oldest = history["CLAUDE.md"][1]
        assert "thorough" not in oldest.content

    def test_snapshot_has_author(self, changelog_git_project: Path) -> None:
        watcher = ConfigWatcher(str(changelog_git_project), ["CLAUDE.md"])
        history = watcher.get_config_history()
        assert history["CLAUDE.md"][0].author == "Tester"

    def test_nonexistent_file_returns_empty(self, changelog_git_project: Path) -> None:
        watcher = ConfigWatcher(str(changelog_git_project), ["nonexistent.md"])
        history = watcher.get_config_history()
        assert history == {}

    def test_get_watched_files(self, changelog_git_project: Path) -> None:
        watcher = ConfigWatcher(str(changelog_git_project), ["CLAUDE.md", ".cursorrules"])
        found = watcher.get_watched_files()
        assert "CLAUDE.md" in found
        assert ".cursorrules" not in found

    def test_glob_patterns_resolved(self, changelog_git_project: Path) -> None:
        agents_dir = changelog_git_project / ".github" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "review.md").write_text("Review instructions")
        subprocess.run(
            ["git", "add", "."], cwd=changelog_git_project, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add agent"],
            cwd=changelog_git_project, capture_output=True, check=True,
        )

        watcher = ConfigWatcher(str(changelog_git_project), [".github/agents/*.md"])
        found = watcher.get_watched_files()
        assert ".github/agents/review.md" in found

    def test_multiple_files_tracked(self, changelog_git_project: Path) -> None:
        """Multiple config files produce separate history entries."""
        (changelog_git_project / ".cursorrules").write_text("rule 1")
        subprocess.run(
            ["git", "add", "."], cwd=changelog_git_project, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add cursorrules"],
            cwd=changelog_git_project, capture_output=True, check=True,
        )
        watcher = ConfigWatcher(
            str(changelog_git_project), ["CLAUDE.md", ".cursorrules"]
        )
        history = watcher.get_config_history()
        assert "CLAUDE.md" in history
        assert ".cursorrules" in history

    def test_deduplication_across_patterns(self, changelog_git_project: Path) -> None:
        """Same file matched by two patterns should only appear once in history."""
        watcher = ConfigWatcher(str(changelog_git_project), ["CLAUDE.md", "CLAUDE.md"])
        tracked = watcher._resolve_tracked_files()
        assert tracked.count("CLAUDE.md") == 1


class TestConfigSnapshot:
    """Test ConfigSnapshot dataclass."""

    def test_snapshot_fields(self) -> None:
        from datetime import datetime

        snap = ConfigSnapshot(
            path="CLAUDE.md",
            content="# Test",
            commit_sha="abc123",
            timestamp=datetime(2026, 1, 1),
            author="Test User",
        )
        assert snap.path == "CLAUDE.md"
        assert snap.commit_sha == "abc123"
        assert snap.author == "Test User"


class TestWatcherEdgeCases:
    """Edge case tests for ConfigWatcher."""

    def test_handles_git_timeout(self, tmp_path: Path) -> None:
        """Watcher returns empty on git timeout."""
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "T"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        (tmp_path / "f.md").write_text("x")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path, capture_output=True, check=True,
        )

        watcher = ConfigWatcher(str(tmp_path), ["f.md"])
        with patch("licit.changelog.watcher.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=10)
            history = watcher.get_config_history()
        assert history == {}

    def test_empty_watch_patterns(self, tmp_path: Path) -> None:
        watcher = ConfigWatcher(str(tmp_path), [])
        history = watcher.get_config_history()
        assert history == {}

    def test_deleted_file_still_in_history(self, changelog_git_project: Path) -> None:
        """A file that was deleted in worktree but has git history should appear."""
        (changelog_git_project / "CLAUDE.md").unlink()
        subprocess.run(
            ["git", "add", "."], cwd=changelog_git_project, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Delete CLAUDE.md"],
            cwd=changelog_git_project, capture_output=True, check=True,
        )
        watcher = ConfigWatcher(str(changelog_git_project), ["CLAUDE.md"])
        history = watcher.get_config_history()
        # File has 3 commits (add, update, delete) — still tracked
        assert "CLAUDE.md" in history
        assert len(history["CLAUDE.md"]) >= 2
