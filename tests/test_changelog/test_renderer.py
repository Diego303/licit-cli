"""Tests for licit.changelog.renderer — Markdown and JSON output."""

import json
from datetime import datetime

from licit.changelog.renderer import ChangelogRenderer
from licit.core.models import ChangeSeverity, ConfigChange


def _make_change(
    file_path: str = "CLAUDE.md",
    field_path: str = "(content)",
    severity: ChangeSeverity = ChangeSeverity.MINOR,
    description: str = "Updated instructions",
    commit_sha: str | None = "abc12345",
    old_value: str | None = "old",
    new_value: str | None = "new",
) -> ConfigChange:
    return ConfigChange(
        file_path=file_path,
        field_path=field_path,
        old_value=old_value,
        new_value=new_value,
        severity=severity,
        description=description,
        timestamp=datetime(2026, 3, 10, 12, 0),
        commit_sha=commit_sha,
    )


class TestMarkdownRenderer:
    """Test Markdown changelog rendering."""

    def setup_method(self) -> None:
        self.renderer = ChangelogRenderer()

    def test_renders_header(self) -> None:
        changes = [_make_change()]
        output = self.renderer.render(changes, fmt="markdown")
        assert "# Agent Config Changelog" in output

    def test_renders_summary_counts(self) -> None:
        changes = [
            _make_change(severity=ChangeSeverity.MAJOR, description="Model changed"),
            _make_change(severity=ChangeSeverity.MINOR, description="Rules updated"),
            _make_change(severity=ChangeSeverity.PATCH, description="Formatting"),
        ]
        output = self.renderer.render(changes, fmt="markdown")
        assert "**1** major" in output
        assert "**1** minor" in output
        assert "**1** patch" in output

    def test_renders_file_sections(self) -> None:
        changes = [
            _make_change(file_path="CLAUDE.md"),
            _make_change(file_path=".cursorrules"),
        ]
        output = self.renderer.render(changes, fmt="markdown")
        assert "## CLAUDE.md" in output
        assert "## .cursorrules" in output

    def test_renders_severity_labels(self) -> None:
        changes = [_make_change(severity=ChangeSeverity.MAJOR, description="Big change")]
        output = self.renderer.render(changes, fmt="markdown")
        assert "[MAJOR]" in output

    def test_renders_commit_sha(self) -> None:
        changes = [_make_change(commit_sha="deadbeef12345678")]
        output = self.renderer.render(changes, fmt="markdown")
        assert "`deadbeef`" in output

    def test_empty_changes_message(self) -> None:
        output = self.renderer.render([], fmt="markdown")
        assert "No changes detected" in output

    def test_no_commit_sha_omits_parens(self) -> None:
        changes = [_make_change(commit_sha=None)]
        output = self.renderer.render(changes, fmt="markdown")
        assert "(`" not in output


class TestJsonRenderer:
    """Test JSON changelog rendering."""

    def setup_method(self) -> None:
        self.renderer = ChangelogRenderer()

    def test_produces_valid_json(self) -> None:
        changes = [_make_change()]
        output = self.renderer.render(changes, fmt="json")
        data = json.loads(output)
        assert "changes" in data
        assert len(data["changes"]) == 1

    def test_json_fields_present(self) -> None:
        changes = [_make_change(severity=ChangeSeverity.MAJOR)]
        output = self.renderer.render(changes, fmt="json")
        data = json.loads(output)
        entry = data["changes"][0]
        assert entry["file_path"] == "CLAUDE.md"
        assert entry["severity"] == "major"
        assert entry["commit_sha"] == "abc12345"
        assert "timestamp" in entry

    def test_empty_changes_returns_empty_list(self) -> None:
        output = self.renderer.render([], fmt="json")
        data = json.loads(output)
        assert data["changes"] == []
