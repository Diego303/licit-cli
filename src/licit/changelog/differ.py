"""Semantic diff of agent configuration files.

Understands YAML, JSON, and Markdown structure to produce meaningful
field-level diffs rather than raw line diffs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import structlog
import yaml

logger = structlog.get_logger()


@dataclass
class FieldDiff:
    """A single field-level difference between two config versions."""

    field_path: str
    old_value: str | None
    new_value: str | None
    is_addition: bool = False
    is_removal: bool = False


def diff_configs(old_content: str, new_content: str, file_path: str) -> list[FieldDiff]:
    """Produce semantic diffs between two versions of a config file.

    Dispatches to format-specific diffing based on file extension.
    """
    if file_path.endswith((".yaml", ".yml")):
        return _diff_yaml(old_content, new_content)
    if file_path.endswith(".json"):
        return _diff_json(old_content, new_content)
    if file_path.endswith(".md"):
        return _diff_markdown(old_content, new_content)
    return _diff_text(old_content, new_content)


def _diff_yaml(old: str, new: str) -> list[FieldDiff]:
    """Diff two YAML files at the key-value level."""
    try:
        old_data = yaml.safe_load(old) or {}
        new_data = yaml.safe_load(new) or {}
    except yaml.YAMLError as exc:
        logger.debug("yaml_parse_error_in_diff", error=str(exc))
        return [FieldDiff(
            field_path="(parse-error)",
            old_value=None,
            new_value=None,
        )]

    old_dict, new_dict = _coerce_to_dict(old_data, new_data, "yaml")
    return _diff_dicts(old_dict, new_dict, prefix="")


def _diff_json(old: str, new: str) -> list[FieldDiff]:
    """Diff two JSON files at the key-value level."""
    try:
        old_data = json.loads(old) if old.strip() else {}
        new_data = json.loads(new) if new.strip() else {}
    except json.JSONDecodeError as exc:
        logger.debug("json_parse_error_in_diff", error=str(exc))
        return [FieldDiff(
            field_path="(parse-error)",
            old_value=None,
            new_value=None,
        )]

    old_dict, new_dict = _coerce_to_dict(old_data, new_data, "json")
    return _diff_dicts(old_dict, new_dict, prefix="")


def _coerce_to_dict(
    old_data: object, new_data: object, fmt: str
) -> tuple[dict[str, object], dict[str, object]]:
    """Coerce parsed data to dicts, logging when non-dict roots are encountered.

    If the root is a list or scalar, we wrap it so the diff still reports
    a meaningful change instead of silently dropping data.
    """
    if not isinstance(old_data, dict) or not isinstance(new_data, dict):
        logger.debug(
            "non_dict_root_in_config",
            format=fmt,
            old_type=type(old_data).__name__,
            new_type=type(new_data).__name__,
        )

    old_dict: dict[str, object] = (
        old_data if isinstance(old_data, dict) else {"(root)": old_data}
    )
    new_dict: dict[str, object] = (
        new_data if isinstance(new_data, dict) else {"(root)": new_data}
    )
    return old_dict, new_dict


def _diff_dicts(
    old: dict[str, object],
    new: dict[str, object],
    prefix: str,
) -> list[FieldDiff]:
    """Recursively diff two dicts, producing field-path diffs."""
    diffs: list[FieldDiff] = []
    all_keys = sorted(set(list(old.keys()) + list(new.keys())))

    for key in all_keys:
        field_path = f"{prefix}.{key}" if prefix else key
        old_val = old.get(key)
        new_val = new.get(key)

        if old_val == new_val:
            continue

        if isinstance(old_val, dict) and isinstance(new_val, dict):
            diffs.extend(_diff_dicts(old_val, new_val, field_path))
            continue

        diffs.append(FieldDiff(
            field_path=field_path,
            old_value=_to_str(old_val),
            new_value=_to_str(new_val),
            is_addition=old_val is None,
            is_removal=new_val is None,
        ))

    return diffs


def _diff_markdown(old: str, new: str) -> list[FieldDiff]:
    """Diff two Markdown files by section headings and line counts."""
    old_sections = _parse_md_sections(old)
    new_sections = _parse_md_sections(new)

    diffs: list[FieldDiff] = []
    all_headings = sorted(set(list(old_sections.keys()) + list(new_sections.keys())))

    for heading in all_headings:
        old_body = old_sections.get(heading)
        new_body = new_sections.get(heading)

        if old_body == new_body:
            continue

        if old_body is None:
            diffs.append(FieldDiff(
                field_path=f"section:{heading}",
                old_value=None,
                new_value=f"{len((new_body or '').splitlines())} lines",
                is_addition=True,
            ))
        elif new_body is None:
            diffs.append(FieldDiff(
                field_path=f"section:{heading}",
                old_value=f"{len(old_body.splitlines())} lines",
                new_value=None,
                is_removal=True,
            ))
        else:
            old_lines = set(old_body.strip().splitlines())
            new_lines = set(new_body.strip().splitlines())
            added = len(new_lines - old_lines)
            removed = len(old_lines - new_lines)
            diffs.append(FieldDiff(
                field_path=f"section:{heading}",
                old_value=f"{len(old_body.splitlines())} lines",
                new_value=f"{len(new_body.splitlines())} lines (+{added}/-{removed})",
            ))

    # If no sections detected, fall back to whole-file diff
    if not all_headings and old.strip() != new.strip():
        old_lines = set(old.strip().splitlines())
        new_lines = set(new.strip().splitlines())
        added = len(new_lines - old_lines)
        removed = len(old_lines - new_lines)
        diffs.append(FieldDiff(
            field_path="(content)",
            old_value=f"{len(old.splitlines())} lines",
            new_value=f"{len(new.splitlines())} lines (+{added}/-{removed})",
        ))

    return diffs


def _parse_md_sections(text: str) -> dict[str, str]:
    """Parse markdown into heading → body mapping.

    Ignores headings inside fenced code blocks (``` ... ```).
    """
    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_lines: list[str] = []
    in_code_block = False

    for line in text.splitlines():
        stripped = line.strip()

        # Track fenced code blocks to avoid treating code as headings
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            if current_heading is not None:
                current_lines.append(line)
            continue

        if not in_code_block and stripped.startswith("#"):
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_lines)
            current_heading = stripped.lstrip("#").strip()
            current_lines = []
        elif current_heading is not None:
            current_lines.append(line)

    if current_heading is not None:
        sections[current_heading] = "\n".join(current_lines)

    return sections


def _diff_text(old: str, new: str) -> list[FieldDiff]:
    """Diff two plain text files as a single blob."""
    if old.strip() == new.strip():
        return []

    old_lines = set(old.strip().splitlines())
    new_lines = set(new.strip().splitlines())
    added = len(new_lines - old_lines)
    removed = len(old_lines - new_lines)

    return [FieldDiff(
        field_path="(content)",
        old_value=f"{len(old.splitlines())} lines",
        new_value=f"{len(new.splitlines())} lines (+{added}/-{removed})",
    )]


def _to_str(value: object) -> str | None:
    """Convert a value to a display string, None stays None."""
    if value is None:
        return None
    return str(value)
