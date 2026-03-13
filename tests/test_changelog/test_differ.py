"""Tests for licit.changelog.differ — semantic config diffing."""

from pathlib import Path

from licit.changelog.differ import FieldDiff, diff_configs

FIXTURES = Path(__file__).parent / "fixtures"


class TestDiffYaml:
    """Test YAML config diffing."""

    def test_detects_changed_field(self) -> None:
        old = FIXTURES / "architect_config_v1.yaml"
        new = FIXTURES / "architect_config_v2.yaml"
        diffs = diff_configs(old.read_text(), new.read_text(), "config.yaml")
        paths = [d.field_path for d in diffs]
        assert "llm.model" in paths
        assert "llm.max_tokens" in paths

    def test_detects_added_list_item(self) -> None:
        old = "guardrails:\n  protected_files:\n    - '*.env'\n"
        new = "guardrails:\n  protected_files:\n    - '*.env'\n    - secrets.yaml\n"
        diffs = diff_configs(old, new, "config.yaml")
        assert len(diffs) == 1
        assert diffs[0].field_path == "guardrails.protected_files"

    def test_no_diffs_for_identical(self) -> None:
        content = "model: gpt-4\nprovider: openai\n"
        diffs = diff_configs(content, content, "config.yaml")
        assert diffs == []

    def test_handles_yaml_parse_error(self) -> None:
        diffs = diff_configs("valid: true\n", "{\n  bad: [unclosed\n", "config.yaml")
        assert len(diffs) == 1
        assert diffs[0].field_path == "(parse-error)"

    def test_non_dict_root_yaml_produces_diff(self) -> None:
        """YAML with list root should still produce a diff, not silently drop."""
        old = "- rule1\n- rule2\n"
        new = "- rule1\n- rule3\n"
        diffs = diff_configs(old, new, "rules.yaml")
        assert len(diffs) == 1
        assert diffs[0].field_path == "(root)"

    def test_empty_yaml_vs_populated(self) -> None:
        diffs = diff_configs("", "model: gpt-4\n", "config.yaml")
        assert len(diffs) == 1
        assert diffs[0].field_path == "model"
        assert diffs[0].is_addition


class TestDiffJson:
    """Test JSON config diffing."""

    def test_detects_field_change(self) -> None:
        old = '{"model": "gpt-4", "temperature": 0.7}'
        new = '{"model": "gpt-4.1", "temperature": 0.7}'
        diffs = diff_configs(old, new, "settings.json")
        assert len(diffs) == 1
        assert diffs[0].field_path == "model"
        assert diffs[0].old_value == "gpt-4"
        assert diffs[0].new_value == "gpt-4.1"

    def test_detects_addition_and_removal(self) -> None:
        old = '{"a": 1, "b": 2}'
        new = '{"b": 2, "c": 3}'
        diffs = diff_configs(old, new, "settings.json")
        paths = {d.field_path: d for d in diffs}
        assert len(diffs) == 2
        assert paths["a"].is_removal
        assert paths["c"].is_addition

    def test_handles_json_parse_error(self) -> None:
        diffs = diff_configs("{}", "not json", "settings.json")
        assert len(diffs) == 1
        assert diffs[0].field_path == "(parse-error)"

    def test_non_dict_root_json_produces_diff(self) -> None:
        """JSON array root should produce a diff, not silently drop."""
        old = '[{"id": 1}]'
        new = '[{"id": 2}]'
        diffs = diff_configs(old, new, "data.json")
        assert len(diffs) == 1
        assert diffs[0].field_path == "(root)"

    def test_nested_dict_diff(self) -> None:
        old = '{"llm": {"model": "gpt-4", "temp": 0.7}}'
        new = '{"llm": {"model": "gpt-4.1", "temp": 0.7}}'
        diffs = diff_configs(old, new, "config.json")
        assert len(diffs) == 1
        assert diffs[0].field_path == "llm.model"


class TestDiffMarkdown:
    """Test Markdown diffing."""

    def test_detects_section_changes(self) -> None:
        old = (FIXTURES / "claude_md_v1.md").read_text()
        new = (FIXTURES / "claude_md_v2.md").read_text()
        diffs = diff_configs(old, new, "CLAUDE.md")
        paths = {d.field_path for d in diffs}
        # Exact: changes in Instructions, Rules; addition of Model
        assert "section:Rules" in paths
        assert "section:Model" in paths
        model_diff = [d for d in diffs if d.field_path == "section:Model"][0]
        assert model_diff.is_addition

    def test_detects_new_section(self) -> None:
        old = "# Title\n\nSome text\n"
        new = "# Title\n\nSome text\n\n## New Section\n\nNew content\n"
        diffs = diff_configs(old, new, "AGENTS.md")
        new_section = [d for d in diffs if "New Section" in d.field_path]
        assert len(new_section) == 1
        assert new_section[0].is_addition

    def test_detects_removed_section(self) -> None:
        old = "# Title\n\nText\n\n## Old Section\n\nOld stuff\n"
        new = "# Title\n\nText\n"
        diffs = diff_configs(old, new, "AGENTS.md")
        removed = [d for d in diffs if d.is_removal]
        assert len(removed) == 1
        assert "Old Section" in removed[0].field_path

    def test_no_diffs_identical_markdown(self) -> None:
        text = "# Title\n\nContent here\n"
        diffs = diff_configs(text, text, "README.md")
        assert diffs == []

    def test_headings_inside_code_blocks_ignored(self) -> None:
        old = "# Real\n\nContent\n\n```\n# Not a heading\n```\n"
        new = "# Real\n\nContent changed\n\n```\n# Not a heading\n```\n"
        diffs = diff_configs(old, new, "CLAUDE.md")
        # Should only see one diff for "Real" section, NOT a diff for "Not a heading"
        paths = [d.field_path for d in diffs]
        assert not any("Not a heading" in p for p in paths)

    def test_markdown_without_headings_falls_back(self) -> None:
        old = "Just plain text\nNo headings\n"
        new = "Just plain text\nDifferent text\n"
        diffs = diff_configs(old, new, "CLAUDE.md")
        assert len(diffs) == 1
        assert diffs[0].field_path == "(content)"


class TestDiffText:
    """Test plain text diffing."""

    def test_detects_text_change(self) -> None:
        old = "rule 1\nrule 2\n"
        new = "rule 1\nrule 3\nrule 4\n"
        diffs = diff_configs(old, new, ".cursorrules")
        assert len(diffs) == 1
        assert diffs[0].field_path == "(content)"

    def test_no_diffs_identical_text(self) -> None:
        text = "rule 1\nrule 2\n"
        diffs = diff_configs(text, text, ".cursorrules")
        assert diffs == []

    def test_whitespace_only_difference_ignored(self) -> None:
        old = "rule 1\nrule 2\n"
        new = "rule 1\nrule 2\n  "
        diffs = diff_configs(old, new, ".cursorrules")
        assert diffs == []
