"""Heuristic rules for detecting AI-generated commits."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger()


@dataclass
class HeuristicResult:
    """Result of applying a single heuristic."""

    name: str
    score: float  # 0.0-1.0 contribution toward "AI" classification
    weight: float  # How much this heuristic matters
    reason: str


class AICommitHeuristics:
    """Collection of heuristics to determine if a commit is AI-generated.

    Six heuristics are applied to each commit, each producing a weighted score.
    The final score is a weighted average: 0 = certainly human, 1 = certainly AI.
    """

    # Built-in patterns for known AI agent authors
    DEFAULT_AI_AUTHORS: frozenset[str] = frozenset({
        "claude", "anthropic", "cursor", "copilot", "codex",
        "openai", "devin", "codeium", "tabnine", "architect",
        "github-actions", "bot", "automation",
    })

    # Conventional-commit and AI-style message patterns
    STRONG_MESSAGE_PATTERNS: tuple[str, ...] = (
        r"^(feat|fix|refactor|chore|docs|test|style)(\(.+\))?:",
        r"implement(ed|s)?\s+\w+",
        r"add(ed|s)?\s+(support|handling|validation|tests?)\s+for",
        r"update(d|s)?\s+\w+\s+(to|for|with)",
        r"generat(ed|e)\s+by",
        r"auto[-\s]?generat",
        r"\[ai\]|\[bot\]|\[agent\]",
    )

    # Co-author keywords that indicate AI involvement
    AI_COAUTHOR_KEYWORDS: frozenset[str] = frozenset({
        "claude", "copilot", "cursor", "ai", "bot", "anthropic",
        "openai", "codex", "devin",
    })

    # File patterns frequently seen in AI-generated commits
    AI_FILE_PATTERNS: tuple[str, ...] = (
        r"__tests__/.+\.test\.",
        r"test_.+\.py$",
        r"\.spec\.(ts|js)$",
    )

    def __init__(self, patterns_file: str | None = None) -> None:
        self._custom_authors: set[str] = set()
        self._custom_message_patterns: list[str] = []
        if patterns_file:
            self._load_patterns(patterns_file)

    def score_commit(self, commit: object) -> tuple[float, list[str]]:
        """Score a commit. Returns (score, reasons) where score 0=human, 1=AI.

        The commit object must have attributes: author, author_email, message,
        files_changed, insertions, deletions, co_authors, date.
        """
        results = [
            self._check_author(commit),
            self._check_message(commit),
            self._check_bulk_changes(commit),
            self._check_co_authors(commit),
            self._check_file_patterns(commit),
            self._check_time_patterns(commit),
        ]

        # Only include heuristics that produced a signal (score > 0) in the average.
        # This prevents non-firing heuristics from diluting strong signals.
        signaling = [r for r in results if r.score > 0]
        if not signaling:
            return 0.0, []

        total_weight = sum(r.weight for r in signaling)
        score = sum(r.score * r.weight for r in signaling) / total_weight
        reasons = [r.reason for r in signaling if r.score > 0.3]

        return min(score, 1.0), reasons

    def _check_author(self, commit: object) -> HeuristicResult:
        """H1: Known AI agent author patterns."""
        author: str = getattr(commit, "author", "")
        email: str = getattr(commit, "author_email", "")
        author_lower = f"{author} {email}".lower()

        all_patterns = self.DEFAULT_AI_AUTHORS | self._custom_authors
        for pattern in all_patterns:
            if pattern in author_lower:
                return HeuristicResult(
                    name="author_pattern",
                    score=0.95,
                    weight=3.0,
                    reason=f"Author matches AI pattern: '{pattern}'",
                )
        return HeuristicResult("author_pattern", 0.0, 3.0, "")

    def _check_message(self, commit: object) -> HeuristicResult:
        """H2: Commit message patterns typical of AI agents."""
        msg: str = getattr(commit, "message", "").lower()

        all_patterns = list(self.STRONG_MESSAGE_PATTERNS) + self._custom_message_patterns
        for pattern in all_patterns:
            try:
                if re.search(pattern, msg):
                    return HeuristicResult(
                        name="message_pattern",
                        score=0.4,
                        weight=1.5,
                        reason="Message matches AI pattern",
                    )
            except re.error:
                logger.debug("invalid_regex_pattern", pattern=pattern)
                continue

        # Weak: very generic messages
        generic = {"misc", "update", "fix", "changes", "wip"}
        if msg.strip() in generic:
            return HeuristicResult("message_pattern", 0.2, 1.0, "Generic message")

        return HeuristicResult("message_pattern", 0.0, 1.5, "")

    def _check_bulk_changes(self, commit: object) -> HeuristicResult:
        """H3: Large number of files or lines changed at once."""
        files_changed: list[str] = getattr(commit, "files_changed", [])
        insertions: int = getattr(commit, "insertions", 0)
        deletions: int = getattr(commit, "deletions", 0)

        files = len(files_changed)
        total_lines = insertions + deletions

        if files > 20 and total_lines > 500:
            return HeuristicResult(
                name="bulk_changes",
                score=0.6,
                weight=2.0,
                reason=f"Bulk change: {files} files, {total_lines} lines",
            )
        if files > 10 and total_lines > 200:
            return HeuristicResult(
                name="bulk_changes",
                score=0.3,
                weight=2.0,
                reason=f"Moderate bulk: {files} files, {total_lines} lines",
            )
        return HeuristicResult("bulk_changes", 0.0, 2.0, "")

    def _check_co_authors(self, commit: object) -> HeuristicResult:
        """H4: Co-authored-by with AI agent names."""
        co_authors: list[str] = getattr(commit, "co_authors", [])
        for co in co_authors:
            co_lower = co.lower()
            if any(kw in co_lower for kw in self.AI_COAUTHOR_KEYWORDS):
                return HeuristicResult(
                    name="co_author",
                    score=0.9,
                    weight=3.0,
                    reason=f"Co-authored-by AI: {co}",
                )
        return HeuristicResult("co_author", 0.0, 3.0, "")

    def _check_file_patterns(self, commit: object) -> HeuristicResult:
        """H5: Files typical of AI-generated code (e.g. all test files)."""
        files_changed: list[str] = getattr(commit, "files_changed", [])
        if not files_changed:
            return HeuristicResult("file_patterns", 0.0, 1.0, "")

        ai_file_count = 0
        for f in files_changed:
            for pattern in self.AI_FILE_PATTERNS:
                if re.search(pattern, f):
                    ai_file_count += 1
                    break

        if ai_file_count > 0 and ai_file_count == len(files_changed):
            return HeuristicResult(
                name="file_patterns",
                score=0.3,
                weight=1.0,
                reason="All files match AI generation patterns",
            )
        return HeuristicResult("file_patterns", 0.0, 1.0, "")

    def _check_time_patterns(self, commit: object) -> HeuristicResult:
        """H6: Commits at unusual hours (1am-5am local time)."""
        from datetime import datetime

        date: datetime | None = getattr(commit, "date", None)
        if date is None:
            return HeuristicResult("time_pattern", 0.0, 0.5, "")

        hour = date.hour
        if 1 <= hour <= 5:
            return HeuristicResult(
                name="time_pattern",
                score=0.3,
                weight=0.5,
                reason=f"Commit at unusual hour: {hour}:00",
            )
        return HeuristicResult("time_pattern", 0.0, 0.5, "")

    def _load_patterns(self, path: str) -> None:
        """Load custom patterns from a JSON file.

        Expected format:
        {
            "ai_authors": ["custom-bot", "my-agent"],
            "message_patterns": ["^\\[auto\\]"]
        }
        """
        p = Path(path)
        if not p.exists():
            logger.debug("custom_patterns_file_not_found", path=path)
            return
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                logger.warning("custom_patterns_invalid_format", path=path)
                return
            authors = data.get("ai_authors", [])
            if isinstance(authors, list):
                self._custom_authors = {str(a).lower() for a in authors}
            patterns = data.get("message_patterns", [])
            if isinstance(patterns, list):
                self._custom_message_patterns = [str(p) for p in patterns]
            logger.info(
                "custom_patterns_loaded",
                path=path,
                authors=len(self._custom_authors),
                patterns=len(self._custom_message_patterns),
            )
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("custom_patterns_load_error", path=path, error=str(exc))
