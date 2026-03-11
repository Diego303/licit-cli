"""Tests for Claude Code session reader."""

from __future__ import annotations

from pathlib import Path

import pytest

from licit.core.models import ProvenanceSource
from licit.provenance.session_readers.claude_code import ClaudeCodeSessionReader


@pytest.fixture
def reader() -> ClaudeCodeSessionReader:
    return ClaudeCodeSessionReader()


class TestAgentName:
    def test_agent_name(self, reader: ClaudeCodeSessionReader) -> None:
        assert reader.agent_name == "claude-code"


class TestReadSessions:
    def test_read_write_tool(self, reader: ClaudeCodeSessionReader, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": "Write", '
            '"params": {"file_path": "src/app.py"}, '
            '"timestamp": "2026-01-15T10:00:00+00:00", '
            '"model": "claude-sonnet-4"}\n',
            encoding="utf-8",
        )
        records = reader.read_sessions([str(tmp_path)])
        assert len(records) == 1
        assert records[0].file_path == "src/app.py"
        assert records[0].source == "ai"
        assert records[0].method == ProvenanceSource.SESSION_LOG
        assert records[0].agent_tool == "claude-code"
        assert records[0].model == "claude-sonnet-4"

    def test_read_edit_tool(self, reader: ClaudeCodeSessionReader, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": "Edit", '
            '"params": {"file_path": "src/utils.py"}, '
            '"timestamp": "2026-01-15T10:30:00+00:00"}\n',
            encoding="utf-8",
        )
        records = reader.read_sessions([str(tmp_path)])
        assert len(records) == 1
        assert records[0].file_path == "src/utils.py"

    def test_skip_non_file_tools(self, reader: ClaudeCodeSessionReader, tmp_path: Path) -> None:
        """Bash commands and non-file tools are skipped."""
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": "Bash", '
            '"params": {"command": "pytest"}}\n'
            '{"type": "tool_use", "tool": "Read", '
            '"params": {"file_path": "src/app.py"}}\n',
            encoding="utf-8",
        )
        records = reader.read_sessions([str(tmp_path)])
        assert len(records) == 0

    def test_skip_non_tool_entries(self, reader: ClaudeCodeSessionReader, tmp_path: Path) -> None:
        """Non-tool_use entries are ignored."""
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "assistant", "content": "Done!"}\n'
            '{"type": "user", "content": "Thanks"}\n',
            encoding="utf-8",
        )
        records = reader.read_sessions([str(tmp_path)])
        assert len(records) == 0

    def test_multiple_files_in_session(
        self, reader: ClaudeCodeSessionReader, tmp_path: Path
    ) -> None:
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": "Write", '
            '"params": {"file_path": "a.py"}, '
            '"timestamp": "2026-01-15T10:00:00+00:00"}\n'
            '{"type": "tool_use", "tool": "Edit", '
            '"params": {"file_path": "b.py"}, '
            '"timestamp": "2026-01-15T10:01:00+00:00"}\n',
            encoding="utf-8",
        )
        records = reader.read_sessions([str(tmp_path)])
        assert len(records) == 2
        assert {r.file_path for r in records} == {"a.py", "b.py"}

    def test_empty_directory(self, reader: ClaudeCodeSessionReader, tmp_path: Path) -> None:
        records = reader.read_sessions([str(tmp_path)])
        assert records == []

    def test_nonexistent_directory(self, reader: ClaudeCodeSessionReader) -> None:
        records = reader.read_sessions(["/nonexistent/path"])
        assert records == []

    def test_nested_session_files(
        self, reader: ClaudeCodeSessionReader, tmp_path: Path
    ) -> None:
        """Reader should find .jsonl files in subdirectories."""
        nested = tmp_path / "project-hash" / "conversations"
        nested.mkdir(parents=True)
        (nested / "conv1.jsonl").write_text(
            '{"type": "tool_use", "tool": "Write", '
            '"params": {"file_path": "x.py"}, '
            '"timestamp": "2026-01-15T10:00:00+00:00"}\n',
            encoding="utf-8",
        )
        records = reader.read_sessions([str(tmp_path)])
        assert len(records) == 1

    def test_malformed_json_lines_skipped(
        self, reader: ClaudeCodeSessionReader, tmp_path: Path
    ) -> None:
        session = tmp_path / "session.jsonl"
        session.write_text(
            'NOT JSON\n'
            '{"type": "tool_use", "tool": "Write", '
            '"params": {"file_path": "ok.py"}, '
            '"timestamp": "2026-01-15T10:00:00+00:00"}\n'
            '{broken json\n',
            encoding="utf-8",
        )
        records = reader.read_sessions([str(tmp_path)])
        assert len(records) == 1
        assert records[0].file_path == "ok.py"

    def test_invalid_timestamp_still_creates_record(
        self, reader: ClaudeCodeSessionReader, tmp_path: Path
    ) -> None:
        """Invalid timestamps fall back to now() with warning."""
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": "Write", '
            '"params": {"file_path": "x.py"}, '
            '"timestamp": "not-a-date"}\n',
            encoding="utf-8",
        )
        records = reader.read_sessions([str(tmp_path)])
        assert len(records) == 1
        assert records[0].file_path == "x.py"

    def test_missing_file_path_skipped(
        self, reader: ClaudeCodeSessionReader, tmp_path: Path
    ) -> None:
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": "Write", "params": {}}\n',
            encoding="utf-8",
        )
        records = reader.read_sessions([str(tmp_path)])
        assert len(records) == 0

    def test_session_id_from_filename(
        self, reader: ClaudeCodeSessionReader, tmp_path: Path
    ) -> None:
        session = tmp_path / "my-session-123.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": "Write", '
            '"params": {"file_path": "x.py"}, '
            '"timestamp": "2026-01-15T10:00:00+00:00"}\n',
            encoding="utf-8",
        )
        records = reader.read_sessions([str(tmp_path)])
        assert records[0].session_id == "my-session-123"
