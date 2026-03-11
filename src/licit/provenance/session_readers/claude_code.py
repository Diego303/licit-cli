"""Read Claude Code session logs to extract provenance data."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import structlog

from licit.core.models import ProvenanceRecord, ProvenanceSource

logger = structlog.get_logger()

# Default location for Claude Code project data
_DEFAULT_CLAUDE_DIR = Path.home() / ".claude" / "projects"


class ClaudeCodeSessionReader:
    """Reads Claude Code session logs and extracts file provenance.

    Claude Code stores session data as JSONL files in
    ~/.claude/projects/<project-hash>/.
    """

    @property
    def agent_name(self) -> str:
        return "claude-code"

    def read_sessions(self, session_dirs: list[str]) -> list[ProvenanceRecord]:
        """Read Claude Code sessions from given directories.

        Falls back to the default ~/.claude/projects/ if no dirs provided.
        """
        dirs = [Path(d) for d in session_dirs] if session_dirs else [_DEFAULT_CLAUDE_DIR]
        records: list[ProvenanceRecord] = []

        for directory in dirs:
            if not directory.exists():
                logger.debug("session_dir_not_found", path=str(directory))
                continue
            records.extend(self._scan_directory(directory))

        logger.info(
            "claude_sessions_read",
            directories=len(dirs),
            records=len(records),
        )
        return records

    def _scan_directory(self, directory: Path) -> list[ProvenanceRecord]:
        """Scan a directory tree for JSONL session files."""
        records: list[ProvenanceRecord] = []

        # Look for JSONL files in the directory tree
        for jsonl_file in directory.rglob("*.jsonl"):
            records.extend(self._parse_session_file(jsonl_file))

        return records

    def _parse_session_file(self, file_path: Path) -> list[ProvenanceRecord]:
        """Parse a single JSONL session file for file modifications."""
        records: list[ProvenanceRecord] = []
        session_id = file_path.stem

        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.debug("session_file_read_error", path=str(file_path), error=str(exc))
            return []

        for line_num, line in enumerate(content.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                if not isinstance(entry, dict):
                    continue
                extracted = self._extract_from_entry(entry, session_id)
                records.extend(extracted)
            except json.JSONDecodeError:
                logger.debug(
                    "session_entry_parse_error",
                    file=str(file_path),
                    line=line_num,
                )

        return records

    def _extract_from_entry(
        self, entry: dict[str, object], session_id: str
    ) -> list[ProvenanceRecord]:
        """Extract provenance records from a single session log entry.

        Looks for tool_use events that write or edit files.
        """
        records: list[ProvenanceRecord] = []

        # Detect tool use entries that modify files
        entry_type = entry.get("type", "")
        if entry_type != "tool_use":
            return records

        tool_name = entry.get("tool", "")
        if not isinstance(tool_name, str):
            return records

        # File-modifying tools: Write, Edit, Bash (with file creation)
        file_path: str | None = None
        raw_params = entry.get("params")
        params: dict[str, object] = raw_params if isinstance(raw_params, dict) else {}

        if tool_name in ("Write", "Edit"):
            fp = params.get("file_path", "")
            if isinstance(fp, str) and fp:
                file_path = fp
        elif tool_name == "Bash":
            # Heuristic: check if command creates files
            if params:
                cmd = params.get("command", "")
                if isinstance(cmd, str) and (">" in cmd or "tee" in cmd or "cp" in cmd):
                    # Can't reliably determine file — skip for V0
                    return records

        if not file_path:
            return records

        # Extract timestamp
        ts_raw = entry.get("timestamp", "")
        try:
            timestamp = (
                datetime.fromisoformat(str(ts_raw)) if ts_raw else datetime.now()
            )
        except (ValueError, TypeError):
            logger.warning(
                "session_entry_invalid_timestamp",
                raw_value=str(ts_raw)[:100],
                file_path=file_path,
            )
            timestamp = datetime.now()

        # Extract model if available
        model = entry.get("model")
        model_str = str(model) if isinstance(model, str) else None

        records.append(ProvenanceRecord(
            file_path=file_path,
            source="ai",
            confidence=0.95,
            method=ProvenanceSource.SESSION_LOG,
            timestamp=timestamp,
            agent_tool="claude-code",
            model=model_str,
            session_id=session_id,
        ))

        return records
