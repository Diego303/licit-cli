"""Infer AI authorship from git history using heuristics."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import structlog

from licit.core.models import ProvenanceRecord, ProvenanceSource
from licit.provenance.heuristics import AICommitHeuristics

logger = structlog.get_logger()

# Field separator used in git log format (null byte)
_FIELD_SEP = "\x01"
# Record separator used between commits (null byte)
_RECORD_SEP = "\x00"


@dataclass
class CommitInfo:
    """Parsed git commit with metadata for heuristic analysis."""

    sha: str
    author: str
    author_email: str
    date: datetime
    message: str
    files_changed: list[str]
    insertions: int
    deletions: int
    co_authors: list[str] = field(default_factory=list)


class GitAnalyzer:
    """Analyzes git history to infer which code was AI-generated.

    Uses heuristic scoring to classify each commit's files as
    ai, human, or mixed provenance.
    """

    # Model name patterns found in commit messages or co-author trailers
    MODEL_PATTERNS: dict[str, str] = {
        r"claude[\s-]*opus[\s-]*4": "claude-opus-4",
        r"claude[\s-]*sonnet[\s-]*4": "claude-sonnet-4",
        r"claude[\s-]*haiku": "claude-haiku",
        r"gpt[\s-]*4\.?1": "gpt-4.1",
        r"gpt[\s-]*4o": "gpt-4o",
        r"o[13][\s-]*(mini|pro)?": "o1",
        r"gemini": "gemini",
        r"deepseek": "deepseek",
    }

    # Agent tool identification from author/email/message
    AGENT_PATTERNS: dict[str, str] = {
        "claude": "claude-code",
        "anthropic": "claude-code",
        "cursor": "cursor",
        "copilot": "copilot",
        "codex": "codex",
        "openai": "codex",
        "architect": "architect",
        "devin": "devin",
    }

    def __init__(
        self,
        root_dir: str,
        heuristics: AICommitHeuristics | None = None,
    ) -> None:
        self.root = Path(root_dir)
        self.heuristics = heuristics or AICommitHeuristics()

    def analyze(self, since: str | None = None) -> list[ProvenanceRecord]:
        """Analyze git history and return provenance records."""
        commits = self._get_commits(since)
        records: list[ProvenanceRecord] = []

        for commit in commits:
            score, _reasons = self.heuristics.score_commit(commit)
            if score >= 0.5:
                source = "ai" if score >= 0.7 else "mixed"
                for file_path in commit.files_changed:
                    records.append(ProvenanceRecord(
                        file_path=file_path,
                        source=source,
                        confidence=score,
                        method=ProvenanceSource.GIT_INFER,
                        timestamp=commit.date,
                        agent_tool=self._infer_agent(commit),
                        model=self._infer_model(commit),
                        session_id=commit.sha[:12],
                    ))
            else:
                for file_path in commit.files_changed:
                    records.append(ProvenanceRecord(
                        file_path=file_path,
                        source="human",
                        confidence=1.0 - score,
                        method=ProvenanceSource.GIT_INFER,
                        timestamp=commit.date,
                    ))

        logger.info(
            "git_analysis_complete",
            commits_analyzed=len(commits),
            records=len(records),
            ai_files=sum(1 for r in records if r.source == "ai"),
        )
        return records

    def _get_commits(self, since: str | None) -> list[CommitInfo]:
        """Get parsed commits from git log."""
        # Use git's %xNN hex escapes to produce \x00 and \x01 in output
        # without embedding actual null bytes in the command-line argument.
        fmt = "%x00" + "%x01".join(["%H", "%an", "%ae", "%aI", "%s", "%b"])
        cmd = ["git", "log", f"--format={fmt}", "--numstat"]
        if since:
            cmd.append(f"--since={since}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.root),
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            logger.warning("git_log_timeout", root=str(self.root))
            return []

        if result.returncode != 0:
            logger.warning(
                "git_log_failed",
                returncode=result.returncode,
                stderr=result.stderr[:200] if result.stderr else "",
            )
            return []

        return self._parse_git_log(result.stdout)

    def _parse_git_log(self, output: str) -> list[CommitInfo]:
        """Parse git log output into CommitInfo objects.

        Uses null-byte record separators and SOH field separators
        for robust parsing even with pipe characters in messages.
        """
        commits: list[CommitInfo] = []
        blocks = output.split(_RECORD_SEP)

        for block in blocks:
            if not block.strip():
                continue

            lines = block.split("\n")
            # Separate header lines from numstat lines
            header_parts: list[str] = []
            numstat_lines: list[str] = []
            in_numstat = False

            for line in lines:
                if re.match(r"^[\d-]+\t[\d-]+\t", line):
                    in_numstat = True
                if in_numstat:
                    numstat_lines.append(line)
                else:
                    header_parts.append(line)

            header = "\n".join(header_parts)
            fields = header.split(_FIELD_SEP, 5)
            if len(fields) < 5:
                continue

            sha = fields[0].strip()
            author = fields[1].strip()
            email = fields[2].strip()
            date_str = fields[3].strip()
            subject = fields[4].strip()
            body = fields[5].strip() if len(fields) > 5 else ""

            # Extract co-authors from body (case-insensitive)
            co_authors = re.findall(
                r"co-authored-by:\s*(.+?)(?:\s*<[^>]+>)?\s*$",
                body,
                re.MULTILINE | re.IGNORECASE,
            )

            # Parse numstat
            files: list[str] = []
            insertions = 0
            deletions = 0
            for line in numstat_lines:
                parts = line.split("\t", 2)
                if len(parts) == 3:
                    try:
                        ins = int(parts[0]) if parts[0] != "-" else 0
                        dels = int(parts[1]) if parts[1] != "-" else 0
                        files.append(parts[2])
                        insertions += ins
                        deletions += dels
                    except ValueError:
                        continue

            try:
                commits.append(CommitInfo(
                    sha=sha,
                    author=author,
                    author_email=email,
                    date=datetime.fromisoformat(date_str),
                    message=subject,
                    files_changed=files,
                    insertions=insertions,
                    deletions=deletions,
                    co_authors=co_authors,
                ))
            except (ValueError, IndexError) as exc:
                logger.debug("commit_parse_error", sha=sha[:8], error=str(exc))

        return commits

    def _infer_agent(self, commit: CommitInfo) -> str | None:
        """Infer which agent tool made this commit."""
        text = f"{commit.author} {commit.author_email} {commit.message}".lower()
        for keyword, agent in self.AGENT_PATTERNS.items():
            if keyword in text:
                return agent
        return None

    def _infer_model(self, commit: CommitInfo) -> str | None:
        """Infer which model was used (from commit message or co-author)."""
        full_text = f"{commit.message} {' '.join(commit.co_authors)}"
        for pattern, model in self.MODEL_PATTERNS.items():
            if re.search(pattern, full_text, re.IGNORECASE):
                return model
        return None
