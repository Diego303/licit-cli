"""Classify agent config changes as MAJOR / MINOR / PATCH.

Uses the semantic diffs from differ.py to assign severity levels based on
which fields changed and whether values were added or removed.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from licit.changelog.differ import FieldDiff, diff_configs
from licit.core.models import ChangeSeverity, ConfigChange

logger = structlog.get_logger()


# Fields whose change indicates a MAJOR severity bump
_MAJOR_FIELDS: frozenset[str] = frozenset({
    "model",
    "llm.model",
    "agent.model",
    "provider",
    "backend",
    "llm.provider",
})

# Fields whose change indicates a MINOR severity bump
_MINOR_FIELDS: frozenset[str] = frozenset({
    "system_prompt",
    "prompt",
    "instructions",
    "guardrails",
    "rules",
    "quality_gates",
    "tools",
    "allowed_tools",
    "blocked_commands",
    "protected_files",
})


class ChangeClassifier:
    """Classifies changes in agent configuration files by severity.

    Severity rules:
    - MAJOR: model/provider change, or removal of a MINOR-level field (escalation)
    - MINOR: prompt/guardrail/tool changes, markdown section edits
    - PATCH: everything else (parameter tweaks, formatting)
    """

    def classify_changes(
        self,
        old_content: str,
        new_content: str,
        file_path: str,
        commit_sha: str | None = None,
        timestamp: datetime | None = None,
    ) -> list[ConfigChange]:
        """Classify all changes between two versions of a config file.

        Returns a list of ConfigChange with severity assigned.
        """
        diffs = diff_configs(old_content, new_content, file_path)
        if not diffs:
            return []

        ts = timestamp or datetime.now(tz=UTC)
        changes: list[ConfigChange] = []

        for diff in diffs:
            severity = _classify_field(diff)
            description = _build_description(diff)
            changes.append(ConfigChange(
                file_path=file_path,
                field_path=diff.field_path,
                old_value=diff.old_value,
                new_value=diff.new_value,
                severity=severity,
                description=description,
                timestamp=ts,
                commit_sha=commit_sha,
            ))

        return changes


def _field_matches(field_path: str, pattern: str) -> bool:
    """Check if a dotted field path matches a pattern by segment.

    Matches if the pattern equals the full path or any trailing segment.
    Example: field "llm.model" matches pattern "model" and "llm.model",
    but field "model_config" does NOT match pattern "model".
    """
    segments = field_path.split(".")
    pattern_segments = pattern.split(".")
    n = len(pattern_segments)
    # Check if pattern matches the last N segments of the field path
    return segments[-n:] == pattern_segments


def _classify_field(diff: FieldDiff) -> ChangeSeverity:
    """Determine severity for a single field diff."""
    field_lower = diff.field_path.lower()

    # Check MAJOR fields (segment-based matching to avoid false positives)
    for major in _MAJOR_FIELDS:
        if _field_matches(field_lower, major):
            return ChangeSeverity.MAJOR

    # Check MINOR fields — removal of a MINOR field escalates to MAJOR
    for minor in _MINOR_FIELDS:
        if _field_matches(field_lower, minor):
            if diff.is_removal:
                return ChangeSeverity.MAJOR
            return ChangeSeverity.MINOR

    # Markdown section changes default to MINOR
    if field_lower.startswith("section:") or field_lower == "(content)":
        return ChangeSeverity.MINOR

    return ChangeSeverity.PATCH


def _build_description(diff: FieldDiff) -> str:
    """Build a human-readable description of a change."""
    if diff.is_addition:
        return f"Added: {diff.field_path} = {_truncate(diff.new_value)}"
    if diff.is_removal:
        return f"Removed: {diff.field_path} (was {_truncate(diff.old_value)})"
    return (
        f"Changed: {diff.field_path} "
        f"from {_truncate(diff.old_value)} to {_truncate(diff.new_value)}"
    )


def _truncate(value: str | None, max_len: int = 60) -> str:
    """Truncate a value for display."""
    if value is None:
        return "(none)"
    return value[:max_len] + "..." if len(value) > max_len else value
