"""Detect and monitor agent configuration files across git history."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import structlog

logger = structlog.get_logger()


@dataclass
class ConfigSnapshot:
    """Snapshot of a config file at a point in time."""

    path: str
    content: str
    commit_sha: str
    timestamp: datetime
    author: str


class ConfigWatcher:
    """Watches agent config files for changes across git history.

    Uses git log to retrieve historical versions of watched config files,
    returning ordered snapshots that can be diffed by the classifier.
    """

    def __init__(self, root_dir: str, watch_patterns: list[str]) -> None:
        self.root = Path(root_dir)
        self.watch_patterns = watch_patterns

    def get_watched_files(self) -> list[str]:
        """Return list of watched config files that currently exist."""
        found: list[str] = []
        for pattern in self.watch_patterns:
            if "*" in pattern:
                for match in sorted(self.root.glob(pattern)):
                    if match.is_file():
                        found.append(str(match.relative_to(self.root)))
            else:
                candidate = self.root / pattern
                if candidate.is_file():
                    found.append(pattern)
        return found

    def get_config_history(
        self, since: str | None = None
    ) -> dict[str, list[ConfigSnapshot]]:
        """Get history of changes for all watched config files.

        Returns a dict mapping relative file paths to lists of ConfigSnapshot,
        ordered newest-first. Only files with at least one commit are included.
        """
        history: dict[str, list[ConfigSnapshot]] = {}

        # Resolve patterns to actual files that exist in git history
        tracked = self._resolve_tracked_files()

        for rel_path in tracked:
            snapshots = self._get_file_history(rel_path, since)
            if snapshots:
                history[rel_path] = snapshots

        return history

    def _resolve_tracked_files(self) -> list[str]:
        """Resolve watch patterns to files tracked by git."""
        tracked: list[str] = []
        seen: set[str] = set()

        for pattern in self.watch_patterns:
            if "*" in pattern:
                for match in sorted(self.root.glob(pattern)):
                    if match.is_file():
                        rel = str(match.relative_to(self.root))
                        if rel not in seen:
                            seen.add(rel)
                            tracked.append(rel)
            elif pattern not in seen and self._file_has_git_history(pattern):
                seen.add(pattern)
                tracked.append(pattern)

        return tracked

    # Maximum content size to load from git show (1 MB). Config files should
    # never be this large; guard against accidental binary tracking.
    _MAX_CONTENT_BYTES: int = 1_048_576

    def _file_has_git_history(self, rel_path: str) -> bool:
        """Check if a file has any commits in git history."""
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-1", "--", rel_path],
                capture_output=True,
                text=True,
                cwd=str(self.root),
                timeout=10,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.debug("git_history_check_timeout", file=rel_path)
            return False
        if result.returncode != 0:
            logger.debug(
                "git_history_check_failed",
                file=rel_path,
                stderr=result.stderr.strip(),
            )
        return result.returncode == 0 and bool(result.stdout.strip())

    def _get_file_history(
        self, rel_path: str, since: str | None
    ) -> list[ConfigSnapshot]:
        """Get git history for a specific file, newest-first."""
        cmd = [
            "git", "log",
            "--format=%H\x01%aI\x01%an",
            "--follow",
            "--", rel_path,
        ]
        if since:
            cmd.insert(2, f"--since={since}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.root),
                timeout=30,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.warning("git_log_timeout", file=rel_path)
            return []

        if result.returncode != 0:
            logger.debug("git_log_failed", file=rel_path, stderr=result.stderr.strip())
            return []

        snapshots: list[ConfigSnapshot] = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\x01", 2)
            if len(parts) < 3:
                logger.debug("malformed_git_log_line", file=rel_path, line=line[:80])
                continue

            sha = parts[0].strip()
            content = self._get_file_at_commit(rel_path, sha)
            if content is None:
                # File was deleted at this commit — record empty content
                content = ""

            try:
                ts = datetime.fromisoformat(parts[1].strip())
            except ValueError:
                logger.debug("invalid_timestamp", sha=sha, raw=parts[1].strip())
                continue

            snapshots.append(ConfigSnapshot(
                path=rel_path,
                content=content,
                commit_sha=sha,
                timestamp=ts,
                author=parts[2].strip(),
            ))

        return snapshots

    def _get_file_at_commit(self, rel_path: str, sha: str) -> str | None:
        """Retrieve file content at a specific commit.

        Returns None if the file doesn't exist at that commit, timed out,
        or exceeds _MAX_CONTENT_BYTES (likely binary/non-config).
        """
        try:
            result = subprocess.run(
                ["git", "show", f"{sha}:{rel_path}"],
                capture_output=True,
                text=True,
                cwd=str(self.root),
                timeout=10,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.debug("git_show_timeout", file=rel_path, sha=sha[:8])
            return None

        if result.returncode != 0:
            return None

        if len(result.stdout.encode("utf-8", errors="replace")) > self._MAX_CONTENT_BYTES:
            logger.warning(
                "config_file_too_large",
                file=rel_path,
                sha=sha[:8],
                max_bytes=self._MAX_CONTENT_BYTES,
            )
            return None

        return result.stdout
