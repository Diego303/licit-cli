"""Tests for the ProvenanceTracker orchestrator."""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from licit.config.schema import ProvenanceConfig
from licit.core.models import ProvenanceRecord, ProvenanceSource
from licit.provenance.tracker import ProvenanceTracker


def _make_config(
    tmp_path: Path,
    methods: list[str] | None = None,
    sign: bool = False,
    enabled: bool = True,
    threshold: float = 0.6,
) -> ProvenanceConfig:
    """Build a ProvenanceConfig for testing."""
    return ProvenanceConfig(
        enabled=enabled,
        methods=methods or ["git-infer"],
        store_path=str(tmp_path / ".licit" / "provenance.jsonl"),
        sign=sign,
        confidence_threshold=threshold,
    )


def _make_git_output(
    sha: str = "a" * 40,
    author: str = "Claude",
    email: str = "claude@anthropic.com",
    date: str = "2026-01-15T14:00:00+00:00",
    message: str = "feat: implement auth",
    files: list[tuple[int, int, str]] | None = None,
) -> str:
    """Build mock git log output."""
    files = files or [(50, 0, "src/auth.py")]
    header = "\x01".join([sha, author, email, date, message, ""])
    numstat = "\n".join(f"{ins}\t{dels}\t{path}" for ins, dels, path in files)
    return f"\x00{header}\n{numstat}"


class TestAnalyze:
    """Test the full analysis pipeline."""

    def test_analyze_stores_records(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        tracker = ProvenanceTracker(str(tmp_path), config)

        git_output = _make_git_output()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=git_output, stderr=""
            )
            records = tracker.analyze()

        assert len(records) >= 1
        # Verify store was written
        store_path = Path(config.store_path)
        assert store_path.exists()

    def test_analyze_with_since(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        tracker = ProvenanceTracker(str(tmp_path), config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            records = tracker.analyze(since="2026-01-01")

        assert records == []
        # Since filtering is now done in Python (by author date),
        # --since is no longer passed to git. Verify the subprocess
        # was still called (git log ran).
        assert mock_run.called

    def test_analyze_disabled(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path, enabled=False)
        tracker = ProvenanceTracker(str(tmp_path), config)
        records = tracker.analyze()
        assert records == []

    def test_analyze_filters_by_threshold(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path, threshold=0.99)
        tracker = ProvenanceTracker(str(tmp_path), config)

        # Human commit with low AI score — confidence will be 1-score
        # which for a human commit should be high, so it should pass
        git_output = _make_git_output(
            author="Jane Dev",
            email="jane@company.com",
            message="Fix bug",
            files=[(5, 3, "src/main.py")],
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=git_output, stderr=""
            )
            records = tracker.analyze()

        # Human records always pass threshold filter
        human_records = [r for r in records if r.source == "human"]
        assert len(human_records) >= 1


class TestSigning:
    """Test cryptographic signing integration."""

    def test_sign_records(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        config = _make_config(tmp_path, sign=True)
        tracker = ProvenanceTracker(str(tmp_path), config)

        git_output = _make_git_output()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=git_output, stderr=""
            )
            records = tracker.analyze()

        # AI records should have signatures
        for r in records:
            if r.source in ("ai", "mixed"):
                assert r.signature is not None
                assert len(r.signature) == 64


class TestSessionReading:
    """Test session log reading integration."""

    def test_session_reader_called(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path, methods=["session-log"])
        config.session_dirs = [str(tmp_path / "sessions")]

        # Create a session file
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        session_file = sessions_dir / "test.jsonl"
        session_file.write_text(
            '{"type": "tool_use", "tool": "Write", '
            '"params": {"file_path": "src/app.py"}, '
            '"timestamp": "2026-01-15T10:00:00+00:00", '
            '"model": "claude-sonnet-4"}\n',
            encoding="utf-8",
        )

        tracker = ProvenanceTracker(str(tmp_path), config)
        records = tracker.analyze()

        assert len(records) >= 1
        session_records = [r for r in records if r.method == ProvenanceSource.SESSION_LOG]
        assert len(session_records) == 1
        assert session_records[0].file_path == "src/app.py"
        assert session_records[0].agent_tool == "claude-code"


class TestMultipleMethods:
    """Test combining multiple provenance methods."""

    def test_git_and_session(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path, methods=["git-infer", "session-log"])
        config.session_dirs = [str(tmp_path / "sessions")]

        # Create session data
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        (sessions_dir / "s.jsonl").write_text(
            '{"type": "tool_use", "tool": "Write", '
            '"params": {"file_path": "src/new.py"}, '
            '"timestamp": "2026-01-15T10:00:00+00:00"}\n',
            encoding="utf-8",
        )

        # Mock git
        git_output = _make_git_output(files=[(10, 0, "src/auth.py")])
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=git_output, stderr=""
            )
            tracker = ProvenanceTracker(str(tmp_path), config)
            records = tracker.analyze()

        git_records = [r for r in records if r.method == ProvenanceSource.GIT_INFER]
        session_records = [r for r in records if r.method == ProvenanceSource.SESSION_LOG]
        assert len(git_records) >= 1
        assert len(session_records) >= 1
