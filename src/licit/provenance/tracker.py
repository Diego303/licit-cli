"""ProvenanceTracker — orchestrates provenance analysis from all sources."""

from __future__ import annotations

from dataclasses import asdict

import structlog

from licit.config.schema import ProvenanceConfig
from licit.core.models import ProvenanceRecord
from licit.provenance.attestation import ProvenanceAttestor
from licit.provenance.git_analyzer import GitAnalyzer
from licit.provenance.session_readers.claude_code import ClaudeCodeSessionReader
from licit.provenance.store import ProvenanceStore

logger = structlog.get_logger()


class ProvenanceTracker:
    """Orchestrates provenance analysis from git history, session logs, and attestation.

    Combines results from:
    - GitAnalyzer (git-infer): heuristic analysis of git commits
    - SessionReaders (session-log): parse agent session files
    - Attestation (optional): cryptographic signing of records
    """

    def __init__(self, root_dir: str, config: ProvenanceConfig) -> None:
        self.root_dir = root_dir
        self.config = config
        self.store = ProvenanceStore(config.store_path)

    def analyze(self, since: str | None = None) -> list[ProvenanceRecord]:
        """Run full provenance analysis and store results.

        Args:
            since: Optional date or tag to limit git history analysis.

        Returns:
            All provenance records collected in this run.
        """
        if not self.config.enabled:
            logger.info("provenance_disabled")
            return []

        all_records: list[ProvenanceRecord] = []

        # Git-based inference
        if "git-infer" in self.config.methods:
            git_records = self._analyze_git(since)
            all_records.extend(git_records)

        # Session log reading
        if "session-log" in self.config.methods:
            session_records = self._read_sessions()
            all_records.extend(session_records)

        # Filter by confidence threshold
        threshold = self.config.confidence_threshold
        filtered = [r for r in all_records if r.confidence >= threshold or r.source == "human"]

        # Sign records if configured
        if self.config.sign:
            self._sign_records(filtered)

        # Store results
        self.store.append(filtered)

        logger.info(
            "provenance_analysis_complete",
            total_records=len(filtered),
            ai_files=sum(1 for r in filtered if r.source == "ai"),
            human_files=sum(1 for r in filtered if r.source == "human"),
            mixed_files=sum(1 for r in filtered if r.source == "mixed"),
        )

        return filtered

    def _analyze_git(self, since: str | None) -> list[ProvenanceRecord]:
        """Run git history analysis."""
        analyzer = GitAnalyzer(self.root_dir)
        records = analyzer.analyze(since=since)
        logger.info("git_analysis_done", records=len(records))
        return records

    def _read_sessions(self) -> list[ProvenanceRecord]:
        """Read session logs from configured session readers."""
        records: list[ProvenanceRecord] = []

        # Claude Code session reader
        reader = ClaudeCodeSessionReader()
        session_records = reader.read_sessions(self.config.session_dirs)
        records.extend(session_records)

        logger.info("session_reading_done", records=len(records))
        return records

    def _sign_records(self, records: list[ProvenanceRecord]) -> None:
        """Sign all records with cryptographic attestation."""
        attestor = ProvenanceAttestor(self.config.sign_key_path)
        for record in records:
            data = asdict(record)
            data["timestamp"] = record.timestamp.isoformat()
            record.signature = attestor.sign_record(data)
        logger.info("records_signed", count=len(records))
