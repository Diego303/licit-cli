"""QA edge case tests for Phase 3 — Changelog.

Covers gaps not addressed by the module-level tests:
- CLI command invocation
- No-git-repo scenarios
- Unicode content
- Single-commit files (no diff possible)
- Timezone-aware vs naive timestamp mixing
- Empty/null config values
"""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from licit.changelog.classifier import ChangeClassifier
from licit.changelog.differ import diff_configs
from licit.changelog.renderer import ChangelogRenderer
from licit.changelog.watcher import ConfigWatcher
from licit.cli import main
from licit.core.models import ChangeSeverity, ConfigChange


# ---------------------------------------------------------------------------
# CLI command tests
# ---------------------------------------------------------------------------

class TestChangelogCLI:
    """Test the `licit changelog` CLI command end-to-end."""

    def test_changelog_no_git_repo(self, tmp_path: Path) -> None:
        """Running changelog outside a git repo prints a message, doesn't crash."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / ".licit.yaml").write_text(
                "changelog:\n  watch_files:\n    - CLAUDE.md\n  output_path: .licit/changelog.md\n"
            )
            result = runner.invoke(main, ["changelog"])
            # Should not crash — either prints "no changes" or a graceful error
            assert result.exit_code == 0
            assert "No agent configuration changes found" in result.output

    def test_changelog_with_real_git_history(self, tmp_path: Path) -> None:
        """Full CLI invocation in a git repo with config changes."""
        # Set up git repo with changes
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "qa@test.com"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "QA"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        (tmp_path / "CLAUDE.md").write_text("# Rules\n\nOld rules\n")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        (tmp_path / "CLAUDE.md").write_text("# Rules\n\nNew rules\n")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "update"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        (tmp_path / ".licit.yaml").write_text(
            "changelog:\n  watch_files:\n    - CLAUDE.md\n"
            "  output_path: .licit/changelog.md\n"
        )
        (tmp_path / ".licit").mkdir()

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path) as d:
            import os
            os.chdir(tmp_path)
            result = runner.invoke(main, ["changelog"])

        assert result.exit_code == 0
        assert "Agent Config Changelog" in result.output

    def test_changelog_json_format(self, tmp_path: Path) -> None:
        """CLI --format json produces valid JSON output."""
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "qa@test.com"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "QA"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        (tmp_path / "CLAUDE.md").write_text("# V1\n\nContent\n")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "v1"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        (tmp_path / "CLAUDE.md").write_text("# V2\n\nDifferent\n")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "v2"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        (tmp_path / ".licit.yaml").write_text(
            "changelog:\n  watch_files:\n    - CLAUDE.md\n"
            "  output_path: .licit/changelog.md\n"
        )
        (tmp_path / ".licit").mkdir()

        runner = CliRunner()
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(main, ["changelog", "--format", "json"])
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0
        # Output contains JSON blob followed by "Changelog saved to" message.
        # Verify the JSON is present in the output and parseable.
        assert '"changes"' in result.output
        # With --format json the file is saved with .json extension
        saved = (tmp_path / ".licit" / "changelog.json").read_text(encoding="utf-8")
        data = json.loads(saved)
        assert "changes" in data


# ---------------------------------------------------------------------------
# Watcher edge cases
# ---------------------------------------------------------------------------

class TestWatcherNoGit:
    """Watcher behavior when git is not initialized."""

    def test_no_git_returns_empty(self, tmp_path: Path) -> None:
        """No git repo → no history, no crash."""
        (tmp_path / "CLAUDE.md").write_text("# Instructions\n")
        watcher = ConfigWatcher(str(tmp_path), ["CLAUDE.md"])
        history = watcher.get_config_history()
        assert history == {}

    def test_get_watched_files_works_without_git(self, tmp_path: Path) -> None:
        """get_watched_files only checks filesystem, not git."""
        (tmp_path / "CLAUDE.md").write_text("# Instructions\n")
        watcher = ConfigWatcher(str(tmp_path), ["CLAUDE.md"])
        found = watcher.get_watched_files()
        assert "CLAUDE.md" in found


class TestWatcherSingleCommit:
    """Files with only one commit have no pair to diff."""

    def test_single_commit_file_has_one_snapshot(self, tmp_path: Path) -> None:
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "T"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        (tmp_path / "CLAUDE.md").write_text("initial")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "only commit"],
            cwd=tmp_path, capture_output=True, check=True,
        )

        watcher = ConfigWatcher(str(tmp_path), ["CLAUDE.md"])
        history = watcher.get_config_history()
        assert "CLAUDE.md" in history
        assert len(history["CLAUDE.md"]) == 1

    def test_single_snapshot_produces_no_changes_in_classifier(
        self, tmp_path: Path,
    ) -> None:
        """The CLI loop skips when range(len(snapshots) - 1) is range(0)."""
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "T"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        (tmp_path / "CLAUDE.md").write_text("single version")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "only"],
            cwd=tmp_path, capture_output=True, check=True,
        )

        watcher = ConfigWatcher(str(tmp_path), ["CLAUDE.md"])
        history = watcher.get_config_history()
        classifier = ChangeClassifier()
        all_changes: list[ConfigChange] = []
        for file_path, snapshots in history.items():
            for i in range(len(snapshots) - 1):
                changes = classifier.classify_changes(
                    old_content=snapshots[i + 1].content,
                    new_content=snapshots[i].content,
                    file_path=file_path,
                )
                all_changes.extend(changes)
        assert all_changes == []


# ---------------------------------------------------------------------------
# Unicode content
# ---------------------------------------------------------------------------

class TestUnicodeHandling:
    """Verify changelog handles non-ASCII content correctly."""

    def test_unicode_in_yaml_values(self) -> None:
        old = "prompt: Hola mundo\n"
        new = "prompt: ¡Hola señor! — con ñ y ü\n"
        diffs = diff_configs(old, new, "config.yaml")
        assert len(diffs) == 1
        assert "ñ" in (diffs[0].new_value or "")

    def test_unicode_in_markdown_sections(self) -> None:
        old = "# Règles\n\nContenu français\n"
        new = "# Règles\n\nContenu modifié avec des accents: éàü\n"
        diffs = diff_configs(old, new, "CLAUDE.md")
        assert len(diffs) >= 1

    def test_unicode_rendered_in_json(self) -> None:
        ch = ConfigChange(
            file_path="config.yaml",
            field_path="prompt",
            old_value="Hola",
            new_value="日本語テスト",
            severity=ChangeSeverity.MINOR,
            description="Changed: prompt",
            timestamp=datetime(2026, 3, 10, tzinfo=UTC),
        )
        renderer = ChangelogRenderer()
        output = renderer.render([ch], fmt="json")
        data = json.loads(output)
        assert data["changes"][0]["new_value"] == "日本語テスト"

    def test_unicode_rendered_in_markdown(self) -> None:
        ch = ConfigChange(
            file_path="config.yaml",
            field_path="prompt",
            old_value="Hola",
            new_value="こんにちは",
            severity=ChangeSeverity.MINOR,
            description="Changed: prompt to こんにちは",
            timestamp=datetime(2026, 3, 10, tzinfo=UTC),
        )
        renderer = ChangelogRenderer()
        output = renderer.render([ch], fmt="markdown")
        assert "こんにちは" in output


# ---------------------------------------------------------------------------
# Timezone mixing
# ---------------------------------------------------------------------------

class TestTimezoneHandling:
    """Verify renderer handles timezone-aware timestamps from git."""

    def test_renderer_sorts_aware_timestamps(self) -> None:
        """Git timestamps are timezone-aware; renderer must handle them."""
        ch1 = ConfigChange(
            file_path="CLAUDE.md",
            field_path="(content)",
            old_value="old",
            new_value="new",
            severity=ChangeSeverity.MINOR,
            description="First change",
            timestamp=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
        )
        ch2 = ConfigChange(
            file_path="CLAUDE.md",
            field_path="model",
            old_value="gpt-4",
            new_value="gpt-5",
            severity=ChangeSeverity.MAJOR,
            description="Model change",
            timestamp=datetime(2026, 3, 11, 12, 0, tzinfo=UTC),
        )
        renderer = ChangelogRenderer()
        # Should not raise — aware timestamps in sort lambda
        output = renderer.render([ch1, ch2], fmt="markdown")
        assert "[MAJOR]" in output
        assert "[MINOR]" in output

    def test_classifier_default_timestamp_is_utc(self) -> None:
        """When no timestamp is passed, classifier should use UTC."""
        classifier = ChangeClassifier()
        changes = classifier.classify_changes(
            "model: gpt-4\n", "model: gpt-5\n", "c.yaml",
        )
        assert len(changes) == 1
        assert changes[0].timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# Differ edge cases
# ---------------------------------------------------------------------------

class TestDifferEdgeCases:
    """Edge cases not covered by main differ tests."""

    def test_empty_string_yaml(self) -> None:
        """Empty YAML string should produce no diffs against empty."""
        diffs = diff_configs("", "", "config.yaml")
        assert diffs == []

    def test_empty_vs_populated_yaml(self) -> None:
        """Empty YAML → populated should produce addition diffs."""
        diffs = diff_configs("", "model: gpt-4\ntemp: 0.7\n", "config.yaml")
        assert len(diffs) == 2
        assert all(d.is_addition for d in diffs)

    def test_nested_type_change_dict_to_scalar(self) -> None:
        """A field going from dict to scalar produces a diff."""
        old = "llm:\n  model: gpt-4\n  temp: 0.7\n"
        new = "llm: disabled\n"
        diffs = diff_configs(old, new, "config.yaml")
        assert len(diffs) == 1
        assert diffs[0].field_path == "llm"

    def test_markdown_only_whitespace_change_between_sections(self) -> None:
        """Whitespace-only changes within a section should still show as diff."""
        old = "# Section\n\nLine 1\nLine 2\n"
        new = "# Section\n\nLine 1\n\nLine 2\n"
        diffs = diff_configs(old, new, "CLAUDE.md")
        # Extra blank line IS a change in section body
        assert len(diffs) == 1

    def test_json_empty_vs_populated(self) -> None:
        diffs = diff_configs("", '{"model": "gpt-4"}', "settings.json")
        assert len(diffs) == 1


# ---------------------------------------------------------------------------
# Classifier edge cases
# ---------------------------------------------------------------------------

class TestClassifierEdgeCases:
    """Classifier edge cases."""

    def test_section_named_model_is_minor_not_major(self) -> None:
        """A markdown section named 'Model' is MINOR — it's documentation, not a config key.

        The segment-based matcher treats 'section:model' as one segment,
        so it does NOT match the MAJOR pattern 'model'. It falls through
        to the startswith("section:") check → MINOR. This is correct.
        """
        old = "# Config\n\nContent\n"
        new = "# Config\n\nContent\n\n## Model\n\nUse gpt-4\n"
        classifier = ChangeClassifier()
        changes = classifier.classify_changes(old, new, "CLAUDE.md")
        model_change = [c for c in changes if "Model" in c.field_path]
        assert len(model_change) == 1
        assert model_change[0].severity == ChangeSeverity.MINOR

    def test_completely_empty_content(self) -> None:
        """Both old and new empty → no changes."""
        classifier = ChangeClassifier()
        changes = classifier.classify_changes("", "", "CLAUDE.md")
        assert changes == []


# ---------------------------------------------------------------------------
# Renderer edge cases
# ---------------------------------------------------------------------------

class TestRendererEdgeCases:
    """Renderer edge cases."""

    def test_very_long_description_in_markdown(self) -> None:
        """Long descriptions don't break markdown formatting."""
        long_desc = "Changed: " + "x" * 200
        ch = ConfigChange(
            file_path="config.yaml",
            field_path="prompt",
            old_value="a",
            new_value="b",
            severity=ChangeSeverity.MINOR,
            description=long_desc,
            timestamp=datetime(2026, 3, 10, tzinfo=UTC),
        )
        renderer = ChangelogRenderer()
        output = renderer.render([ch], fmt="markdown")
        # Should render without error; description is in one line
        assert long_desc in output

    def test_json_null_values(self) -> None:
        """Null old_value/new_value render as null in JSON."""
        ch = ConfigChange(
            file_path="config.yaml",
            field_path="key",
            old_value=None,
            new_value="new",
            severity=ChangeSeverity.MINOR,
            description="Added key",
            timestamp=datetime(2026, 3, 10, tzinfo=UTC),
        )
        renderer = ChangelogRenderer()
        output = renderer.render([ch], fmt="json")
        data = json.loads(output)
        assert data["changes"][0]["old_value"] is None


# ---------------------------------------------------------------------------
# Import safety
# ---------------------------------------------------------------------------

class TestImportSafety:
    """Verify Phase 3 modules import without circular deps."""

    def test_import_watcher(self) -> None:
        from licit.changelog.watcher import ConfigSnapshot, ConfigWatcher
        assert ConfigWatcher is not None
        assert ConfigSnapshot is not None

    def test_import_differ(self) -> None:
        from licit.changelog.differ import FieldDiff, diff_configs
        assert diff_configs is not None
        assert FieldDiff is not None

    def test_import_classifier(self) -> None:
        from licit.changelog.classifier import ChangeClassifier
        assert ChangeClassifier is not None

    def test_import_renderer(self) -> None:
        from licit.changelog.renderer import ChangelogRenderer
        assert ChangelogRenderer is not None
