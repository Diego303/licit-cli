"""Tests for AI commit heuristic scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pytest

from licit.provenance.heuristics import AICommitHeuristics, HeuristicResult


@dataclass
class FakeCommit:
    """Minimal commit object for testing heuristics."""

    author: str = "Jane Dev"
    author_email: str = "jane@company.com"
    message: str = "Fix a bug"
    files_changed: list[str] = field(default_factory=lambda: ["src/main.py"])
    insertions: int = 5
    deletions: int = 3
    co_authors: list[str] = field(default_factory=list)
    date: datetime = field(default_factory=lambda: datetime(2026, 1, 15, 14, 0))


def make_commit(**kwargs: object) -> FakeCommit:
    """Build a FakeCommit with overrides."""
    return FakeCommit(**kwargs)  # type: ignore[arg-type]


class TestAuthorHeuristic:
    """H1: Author name/email patterns."""

    def test_ai_author_claude(self) -> None:
        commit = make_commit(author="Claude", author_email="claude@anthropic.com")
        h = AICommitHeuristics()
        score, reasons = h.score_commit(commit)
        assert score >= 0.8
        assert any("author" in r.lower() for r in reasons)

    def test_ai_author_copilot(self) -> None:
        commit = make_commit(author="GitHub Copilot", author_email="copilot@github.com")
        h = AICommitHeuristics()
        score, reasons = h.score_commit(commit)
        assert score >= 0.7
        assert any("copilot" in r.lower() for r in reasons)

    def test_human_author(self) -> None:
        commit = make_commit(author="Jane Dev", author_email="jane@company.com")
        h = AICommitHeuristics()
        score, _ = h.score_commit(commit)
        assert score < 0.3

    def test_bot_in_email(self) -> None:
        commit = make_commit(author="CI Bot", author_email="bot@ci.com")
        h = AICommitHeuristics()
        score, reasons = h.score_commit(commit)
        assert score >= 0.5
        assert any("bot" in r.lower() for r in reasons)


class TestMessageHeuristic:
    """H2: Commit message patterns."""

    def test_conventional_commit_pattern(self) -> None:
        commit = make_commit(message="feat(auth): implement OAuth2 login flow")
        h = AICommitHeuristics()
        result = h._check_message(commit)
        assert result.score > 0
        assert result.name == "message_pattern"

    def test_implement_pattern(self) -> None:
        commit = make_commit(message="Implemented user authentication")
        h = AICommitHeuristics()
        result = h._check_message(commit)
        assert result.score > 0

    def test_generic_message(self) -> None:
        commit = make_commit(message="fix")
        h = AICommitHeuristics()
        result = h._check_message(commit)
        assert result.score == 0.2

    def test_normal_message(self) -> None:
        commit = make_commit(message="Fix login timeout bug in auth module")
        h = AICommitHeuristics()
        result = h._check_message(commit)
        assert result.score == 0.0


class TestBulkChanges:
    """H3: Bulk change detection."""

    def test_large_bulk_change(self) -> None:
        files = [f"src/file{i}.py" for i in range(25)]
        commit = make_commit(files_changed=files, insertions=800, deletions=200)
        h = AICommitHeuristics()
        score, reasons = h.score_commit(commit)
        assert score >= 0.4
        assert any("bulk" in r.lower() for r in reasons)

    def test_moderate_bulk(self) -> None:
        files = [f"src/file{i}.py" for i in range(12)]
        commit = make_commit(files_changed=files, insertions=250, deletions=50)
        h = AICommitHeuristics()
        result = h._check_bulk_changes(commit)
        assert result.score == 0.3

    def test_small_change(self) -> None:
        commit = make_commit(files_changed=["src/main.py"], insertions=5, deletions=3)
        h = AICommitHeuristics()
        result = h._check_bulk_changes(commit)
        assert result.score == 0.0


class TestCoAuthors:
    """H4: Co-authored-by trailer detection."""

    def test_claude_coauthor(self) -> None:
        commit = make_commit(co_authors=["Claude (Anthropic AI)"])
        h = AICommitHeuristics()
        score, _ = h.score_commit(commit)
        assert score >= 0.7

    def test_copilot_coauthor(self) -> None:
        commit = make_commit(co_authors=["GitHub Copilot"])
        h = AICommitHeuristics()
        result = h._check_co_authors(commit)
        assert result.score == 0.9

    def test_human_coauthor(self) -> None:
        commit = make_commit(co_authors=["John Smith"])
        h = AICommitHeuristics()
        result = h._check_co_authors(commit)
        assert result.score == 0.0

    def test_no_coauthors(self) -> None:
        commit = make_commit(co_authors=[])
        h = AICommitHeuristics()
        result = h._check_co_authors(commit)
        assert result.score == 0.0


class TestFilePatterns:
    """H5: AI-typical file patterns."""

    def test_all_test_files(self) -> None:
        commit = make_commit(files_changed=["test_auth.py", "test_db.py"])
        h = AICommitHeuristics()
        result = h._check_file_patterns(commit)
        assert result.score == 0.3

    def test_mixed_files(self) -> None:
        commit = make_commit(files_changed=["src/main.py", "test_main.py"])
        h = AICommitHeuristics()
        result = h._check_file_patterns(commit)
        assert result.score == 0.0  # Not ALL files are test files

    def test_no_files(self) -> None:
        commit = make_commit(files_changed=[])
        h = AICommitHeuristics()
        result = h._check_file_patterns(commit)
        assert result.score == 0.0


class TestTimePatterns:
    """H6: Unusual time patterns."""

    def test_late_night_commit(self) -> None:
        commit = make_commit(date=datetime(2026, 1, 15, 3, 0))
        h = AICommitHeuristics()
        result = h._check_time_patterns(commit)
        assert result.score == 0.3

    def test_normal_hours(self) -> None:
        commit = make_commit(date=datetime(2026, 1, 15, 14, 0))
        h = AICommitHeuristics()
        result = h._check_time_patterns(commit)
        assert result.score == 0.0


class TestCustomPatterns:
    """Custom pattern loading."""

    def test_load_custom_patterns(self, tmp_path: object) -> None:
        from pathlib import Path

        p = Path(str(tmp_path)) / "patterns.json"
        p.write_text('{"ai_authors": ["mybot"], "message_patterns": ["^\\\\[auto\\\\]"]}')
        h = AICommitHeuristics(patterns_file=str(p))
        commit = make_commit(author="mybot", author_email="mybot@ci.com")
        score, _ = h.score_commit(commit)
        assert score >= 0.5

    def test_missing_patterns_file(self) -> None:
        h = AICommitHeuristics(patterns_file="/nonexistent/patterns.json")
        # Should not raise, just ignore
        commit = make_commit()
        score, _ = h.score_commit(commit)
        assert score < 0.3


class TestHumanCommit:
    """Verify normal human commits score low."""

    def test_typical_human_commit(self) -> None:
        commit = make_commit(
            author="Jane Dev",
            author_email="jane@company.com",
            message="Fix login timeout bug",
            files_changed=["src/auth.py"],
            insertions=5,
            deletions=3,
        )
        h = AICommitHeuristics()
        score, _ = h.score_commit(commit)
        assert score < 0.3
