"""Tests for git history analyzer."""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from licit.provenance.git_analyzer import CommitInfo, GitAnalyzer


@pytest.fixture
def analyzer(tmp_path: Path) -> GitAnalyzer:
    """Create a GitAnalyzer pointed at a temp directory."""
    return GitAnalyzer(str(tmp_path))


def make_git_commit(
    sha: str = "a" * 40,
    author: str = "Jane Dev",
    email: str = "jane@company.com",
    date: str = "2026-01-15T14:00:00+00:00",
    message: str = "Fix a bug",
    files: list[tuple[int, int, str]] | None = None,
    body: str = "",
) -> str:
    """Build a raw git log block matching our format.

    Uses \\x00 as record separator and \\x01 as field separator.
    """
    files = files or [(5, 3, "src/main.py")]
    header = f"\x01".join([sha, author, email, date, message, body])
    numstat = "\n".join(f"{ins}\t{dels}\t{path}" for ins, dels, path in files)
    return f"\x00{header}\n{numstat}"


class TestGitLogParsing:
    """Test parsing of git log output."""

    def test_parse_single_commit(self, analyzer: GitAnalyzer) -> None:
        output = make_git_commit()
        commits = analyzer._parse_git_log(output)
        assert len(commits) == 1
        assert commits[0].sha == "a" * 40
        assert commits[0].author == "Jane Dev"
        assert commits[0].files_changed == ["src/main.py"]
        assert commits[0].insertions == 5
        assert commits[0].deletions == 3

    def test_parse_multiple_commits(self, analyzer: GitAnalyzer) -> None:
        output = (
            make_git_commit(sha="a" * 40, message="First commit")
            + make_git_commit(sha="b" * 40, message="Second commit")
        )
        commits = analyzer._parse_git_log(output)
        assert len(commits) == 2
        assert commits[0].message == "First commit"
        assert commits[1].message == "Second commit"

    def test_parse_commit_with_coauthors(self, analyzer: GitAnalyzer) -> None:
        output = make_git_commit(
            body="Co-authored-by: Claude <claude@anthropic.com>\nSome text",
        )
        commits = analyzer._parse_git_log(output)
        assert len(commits) == 1
        assert "Claude" in commits[0].co_authors

    def test_parse_commit_with_multiple_files(self, analyzer: GitAnalyzer) -> None:
        output = make_git_commit(
            files=[
                (10, 2, "src/auth.py"),
                (20, 5, "src/db.py"),
                (3, 0, "tests/test_auth.py"),
            ],
        )
        commits = analyzer._parse_git_log(output)
        assert len(commits) == 1
        assert len(commits[0].files_changed) == 3
        assert commits[0].insertions == 33
        assert commits[0].deletions == 7

    def test_parse_empty_output(self, analyzer: GitAnalyzer) -> None:
        commits = analyzer._parse_git_log("")
        assert commits == []

    def test_parse_binary_files(self, analyzer: GitAnalyzer) -> None:
        """Binary files show - for insertions/deletions."""
        output = make_git_commit(
            files=[(5, 3, "src/main.py")],
        )
        # Add a binary file numstat line
        output += "\n-\t-\timage.png"
        commits = analyzer._parse_git_log(output)
        assert len(commits) == 1
        assert "image.png" in commits[0].files_changed

    def test_parse_message_with_pipes(self, analyzer: GitAnalyzer) -> None:
        """Messages with pipe characters should parse correctly."""
        output = make_git_commit(message="Fix: a | b | c")
        commits = analyzer._parse_git_log(output)
        assert len(commits) == 1
        assert commits[0].message == "Fix: a | b | c"


class TestAgentInference:
    """Test agent tool inference from commit metadata."""

    def test_infer_claude(self, analyzer: GitAnalyzer) -> None:
        commit = CommitInfo(
            sha="a" * 40,
            author="Claude",
            author_email="claude@anthropic.com",
            date=datetime(2026, 1, 15),
            message="feat: add auth",
            files_changed=[],
            insertions=0,
            deletions=0,
        )
        assert analyzer._infer_agent(commit) == "claude-code"

    def test_infer_cursor(self, analyzer: GitAnalyzer) -> None:
        commit = CommitInfo(
            sha="b" * 40,
            author="cursor-bot",
            author_email="bot@cursor.sh",
            date=datetime(2026, 1, 15),
            message="update",
            files_changed=[],
            insertions=0,
            deletions=0,
        )
        assert analyzer._infer_agent(commit) == "cursor"

    def test_infer_unknown(self, analyzer: GitAnalyzer) -> None:
        commit = CommitInfo(
            sha="c" * 40,
            author="Jane Dev",
            author_email="jane@company.com",
            date=datetime(2026, 1, 15),
            message="fix bug",
            files_changed=[],
            insertions=0,
            deletions=0,
        )
        assert analyzer._infer_agent(commit) is None


class TestModelInference:
    """Test model inference from commit metadata."""

    def test_infer_claude_sonnet(self, analyzer: GitAnalyzer) -> None:
        commit = CommitInfo(
            sha="a" * 40,
            author="Dev",
            author_email="dev@co.com",
            date=datetime(2026, 1, 15),
            message="feat: auth",
            files_changed=[],
            insertions=0,
            deletions=0,
            co_authors=["Claude Sonnet 4 <noreply@anthropic.com>"],
        )
        assert analyzer._infer_model(commit) == "claude-sonnet-4"

    def test_infer_no_model(self, analyzer: GitAnalyzer) -> None:
        commit = CommitInfo(
            sha="b" * 40,
            author="Jane",
            author_email="jane@co.com",
            date=datetime(2026, 1, 15),
            message="fix bug",
            files_changed=[],
            insertions=0,
            deletions=0,
        )
        assert analyzer._infer_model(commit) is None


class TestAnalysis:
    """Test the full analysis pipeline."""

    def test_analyze_with_mocked_git(self, analyzer: GitAnalyzer) -> None:
        """Mock subprocess to test analysis flow."""
        ai_output = make_git_commit(
            sha="a" * 40,
            author="Claude",
            email="claude@anthropic.com",
            message="feat: implement auth module",
            files=[(100, 0, "src/auth.py"), (50, 0, "src/auth_test.py")],
        )
        human_output = make_git_commit(
            sha="b" * 40,
            author="Jane Dev",
            email="jane@company.com",
            message="Fix login timeout bug",
            files=[(5, 3, "src/login.py")],
        )
        combined = ai_output + human_output

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=combined, stderr=""
            )
            records = analyzer.analyze()

        assert len(records) == 3
        ai_records = [r for r in records if r.source in ("ai", "mixed")]
        human_records = [r for r in records if r.source == "human"]
        assert len(ai_records) >= 1
        assert len(human_records) >= 1

    def test_analyze_empty_repo(self, analyzer: GitAnalyzer) -> None:
        """Empty git log output should return empty records."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            records = analyzer.analyze()
        assert records == []

    def test_analyze_git_failure(self, analyzer: GitAnalyzer) -> None:
        """Git command failure should return empty records."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=128, stdout="", stderr="not a git repo"
            )
            records = analyzer.analyze()
        assert records == []
