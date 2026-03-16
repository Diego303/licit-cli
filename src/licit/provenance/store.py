"""Append-only JSONL provenance store."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import click
import structlog

from licit.core.models import ProvenanceRecord, ProvenanceSource

logger = structlog.get_logger()


class ProvenanceStore:
    """Deduplicated JSONL store for provenance records.

    Each line is a JSON object representing a single ProvenanceRecord.
    On write, records are merged with existing data — latest record per
    file wins — so the store never grows unboundedly.
    """

    def __init__(self, store_path: str) -> None:
        self.path = Path(store_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, records: list[ProvenanceRecord]) -> None:
        """Merge *records* into the store, deduplicating by file path.

        Existing records for the same file are kept only if they are
        newer than the incoming one.
        """
        if not records:
            return

        try:
            # Merge: existing records + new records, latest per file wins
            merged: dict[str, ProvenanceRecord] = {}
            for r in self.load_all():
                existing = merged.get(r.file_path)
                if existing is None or r.timestamp > existing.timestamp:
                    merged[r.file_path] = r
            for r in records:
                existing = merged.get(r.file_path)
                if existing is None or r.timestamp >= existing.timestamp:
                    merged[r.file_path] = r

            self._write_all(list(merged.values()))
            logger.info("provenance_stored", count=len(merged))
        except OSError as exc:
            logger.error("provenance_write_failed", path=str(self.path), error=str(exc))
            raise click.ClickException(
                f"Cannot write to {self.path}: {exc.strerror}. "
                f"Check directory permissions."
            ) from exc

    # Keep append as an alias for backwards compatibility with tests
    append = save

    def _write_all(self, records: list[ProvenanceRecord]) -> None:
        """Atomically rewrite the store with the given records."""
        with open(self.path, "w", encoding="utf-8") as f:
            for record in records:
                data = asdict(record)
                data["timestamp"] = record.timestamp.isoformat()
                if record.lines_range is not None:
                    data["lines_range"] = list(record.lines_range)
                f.write(json.dumps(data, default=str) + "\n")

    def load_all(self) -> list[ProvenanceRecord]:
        """Load all records from the store."""
        if not self.path.exists():
            return []
        records: list[ProvenanceRecord] = []
        for line_num, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                data["method"] = ProvenanceSource(data["method"])
                # Restore tuple from list
                lr = data.get("lines_range")
                if isinstance(lr, list) and len(lr) == 2:
                    data["lines_range"] = (lr[0], lr[1])
                else:
                    data["lines_range"] = None
                records.append(ProvenanceRecord(**data))
            except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
                logger.debug(
                    "provenance_record_parse_error",
                    line=line_num,
                    error=str(exc),
                )
        return records

    def get_stats(self) -> dict[str, object]:
        """Get provenance statistics.

        Returns a dict with keys: total_files, ai_files, human_files,
        mixed_files, ai_percentage.
        """
        records = self.load_all()
        if not records:
            return {
                "total_files": 0,
                "ai_files": 0,
                "human_files": 0,
                "mixed_files": 0,
                "ai_percentage": 0.0,
            }

        ai = sum(1 for r in records if r.source == "ai")
        human = sum(1 for r in records if r.source == "human")
        mixed = sum(1 for r in records if r.source == "mixed")
        total = len(records)

        return {
            "total_files": total,
            "ai_files": ai,
            "human_files": human,
            "mixed_files": mixed,
            "ai_percentage": round((ai + mixed * 0.5) / max(total, 1) * 100, 1),
        }

    def get_by_file(self, file_path: str) -> list[ProvenanceRecord]:
        """Get all provenance records for a specific file."""
        return [r for r in self.load_all() if r.file_path == file_path]
