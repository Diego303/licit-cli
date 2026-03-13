"""Tests for licit.changelog.classifier — change severity classification."""

from datetime import datetime
from pathlib import Path

from licit.changelog.classifier import ChangeClassifier, _field_matches
from licit.core.models import ChangeSeverity

FIXTURES = Path(__file__).parent / "fixtures"


class TestFieldMatches:
    """Test the segment-based field matching logic."""

    def test_exact_match(self) -> None:
        assert _field_matches("model", "model")

    def test_trailing_segment_match(self) -> None:
        assert _field_matches("llm.model", "model")

    def test_multi_segment_pattern(self) -> None:
        assert _field_matches("llm.model", "llm.model")

    def test_no_substring_false_positive(self) -> None:
        """'model_config' should NOT match pattern 'model'."""
        assert not _field_matches("model_config", "model")

    def test_no_prefix_false_positive(self) -> None:
        """'some_model' should NOT match pattern 'model'."""
        assert not _field_matches("some_model", "model")

    def test_nested_no_false_positive(self) -> None:
        """'model_config.temperature' should NOT match 'model'."""
        assert not _field_matches("model_config.temperature", "model")

    def test_deep_nesting_matches_leaf(self) -> None:
        assert _field_matches("a.b.c.model", "model")


class TestClassifyYaml:
    """Test classification of YAML config changes."""

    def setup_method(self) -> None:
        self.classifier = ChangeClassifier()

    def test_model_change_is_major(self) -> None:
        old = FIXTURES / "architect_config_v1.yaml"
        new = FIXTURES / "architect_config_v2.yaml"
        changes = self.classifier.classify_changes(
            old.read_text(), new.read_text(), ".architect/config.yaml", commit_sha="abc123"
        )
        model_changes = [c for c in changes if c.field_path == "llm.model"]
        assert len(model_changes) == 1
        assert model_changes[0].severity == ChangeSeverity.MAJOR

    def test_guardrail_addition_is_minor(self) -> None:
        old = "guardrails:\n  protected_files:\n    - '*.env'\n"
        new = "guardrails:\n  protected_files:\n    - '*.env'\n    - secrets.yaml\n"
        changes = self.classifier.classify_changes(old, new, "config.yaml")
        assert len(changes) == 1
        assert changes[0].field_path == "guardrails.protected_files"
        assert changes[0].severity == ChangeSeverity.MINOR

    def test_guardrail_removal_escalates_to_major(self) -> None:
        old = "guardrails:\n  protected_files:\n    - '*.env'\nrules:\n  - no-eval\n"
        new = "guardrails:\n  protected_files:\n    - '*.env'\n"
        changes = self.classifier.classify_changes(old, new, "config.yaml")
        rule_changes = [c for c in changes if c.field_path == "rules"]
        assert len(rule_changes) == 1
        assert rule_changes[0].severity == ChangeSeverity.MAJOR
        assert "Removed" in rule_changes[0].description

    def test_parameter_tweak_is_patch(self) -> None:
        old = "timeout: 30\nretries: 3\n"
        new = "timeout: 60\nretries: 3\n"
        changes = self.classifier.classify_changes(old, new, "config.yaml")
        assert len(changes) == 1
        assert changes[0].severity == ChangeSeverity.PATCH

    def test_commit_sha_propagated(self) -> None:
        old = "model: gpt-4\n"
        new = "model: gpt-4.1\n"
        changes = self.classifier.classify_changes(old, new, "c.yaml", commit_sha="deadbeef")
        assert len(changes) == 1
        assert changes[0].commit_sha == "deadbeef"

    def test_timestamp_propagated(self) -> None:
        ts = datetime(2026, 1, 15, 10, 0)
        old = "model: gpt-4\n"
        new = "model: gpt-4.1\n"
        changes = self.classifier.classify_changes(old, new, "c.yaml", timestamp=ts)
        assert len(changes) == 1
        assert changes[0].timestamp == ts

    def test_no_changes_returns_empty(self) -> None:
        content = "model: gpt-4\nprovider: openai\n"
        changes = self.classifier.classify_changes(content, content, "config.yaml")
        assert changes == []

    def test_provider_change_is_major(self) -> None:
        old = "llm:\n  provider: anthropic\n"
        new = "llm:\n  provider: openai\n"
        changes = self.classifier.classify_changes(old, new, "config.yaml")
        assert len(changes) == 1
        assert changes[0].severity == ChangeSeverity.MAJOR


class TestClassifyMarkdown:
    """Test classification of Markdown config changes."""

    def setup_method(self) -> None:
        self.classifier = ChangeClassifier()

    def test_markdown_section_edits_are_minor(self) -> None:
        old = "# Title\n\n## Rules\n\n- rule 1\n- rule 2\n"
        new = "# Title\n\n## Rules\n\n- rule 1\n- rule 3\n"
        changes = self.classifier.classify_changes(old, new, "CLAUDE.md")
        assert len(changes) >= 1
        for c in changes:
            assert c.severity == ChangeSeverity.MINOR

    def test_descriptions_contain_action_verb(self) -> None:
        old = "# Title\n\nOld content\n"
        new = "# Title\n\nNew content\n"
        changes = self.classifier.classify_changes(old, new, "CLAUDE.md")
        assert len(changes) >= 1
        for c in changes:
            assert any(word in c.description for word in ("Added", "Changed", "Removed"))

    def test_new_section_detected(self) -> None:
        old = "# Title\n\nContent\n"
        new = "# Title\n\nContent\n\n## New Section\n\nMore stuff\n"
        changes = self.classifier.classify_changes(old, new, "AGENTS.md")
        new_sec = [c for c in changes if "New Section" in c.field_path]
        assert len(new_sec) == 1
        assert "Added" in new_sec[0].description

    def test_fixture_changes_produce_multiple_diffs(self) -> None:
        old = (FIXTURES / "claude_md_v1.md").read_text()
        new = (FIXTURES / "claude_md_v2.md").read_text()
        changes = self.classifier.classify_changes(old, new, "CLAUDE.md")
        assert len(changes) >= 2  # At least Rules changed + Model added


class TestClassifyText:
    """Test classification of plain text config changes."""

    def setup_method(self) -> None:
        self.classifier = ChangeClassifier()

    def test_text_content_change_is_minor(self) -> None:
        old = (FIXTURES / "cursorrules_v1.txt").read_text()
        new = old.replace("Never use inline styles.", "Prefer CSS modules.")
        changes = self.classifier.classify_changes(old, new, ".cursorrules")
        assert len(changes) == 1
        assert changes[0].severity == ChangeSeverity.MINOR

    def test_truncation_at_boundary(self) -> None:
        """Values longer than 60 chars are truncated in descriptions."""
        long_value = "x" * 80
        old = f"prompt: short\n"
        new = f"prompt: {long_value}\n"
        changes = self.classifier.classify_changes(old, new, "config.yaml")
        assert len(changes) == 1
        assert "..." in changes[0].description
