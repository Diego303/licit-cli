"""Tests for the append-only JSONL provenance store."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from licit.core.models import ProvenanceRecord, ProvenanceSource
from licit.provenance.store import ProvenanceStore


def make_record(
    file_path: str = "src/main.py",
    source: str = "ai",
    confidence: float = 0.9,
    method: ProvenanceSource = ProvenanceSource.GIT_INFER,
    timestamp: datetime | None = None,
    agent_tool: str | None = "claude-code",
    model: str | None = "claude-sonnet-4",
) -> ProvenanceRecord:
    """Create a test provenance record."""
    return ProvenanceRecord(
        file_path=file_path,
        source=source,
        confidence=confidence,
        method=method,
        timestamp=timestamp or datetime(2026, 1, 15, 10, 0),
        agent_tool=agent_tool,
        model=model,
    )


class TestStoreAppend:
    """Test appending records to the store."""

    def test_append_creates_file(self, tmp_path: Path) -> None:
        store_path = tmp_path / ".licit" / "provenance.jsonl"
        store = ProvenanceStore(str(store_path))
        store.append([make_record()])
        assert store_path.exists()

    def test_append_writes_jsonl(self, tmp_path: Path) -> None:
        store_path = tmp_path / "prov.jsonl"
        store = ProvenanceStore(str(store_path))
        store.append([make_record(), make_record(file_path="src/utils.py")])
        lines = store_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_append_is_additive(self, tmp_path: Path) -> None:
        store_path = tmp_path / "prov.jsonl"
        store = ProvenanceStore(str(store_path))
        store.append([make_record()])
        store.append([make_record(file_path="src/other.py")])
        lines = store_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_append_empty_list(self, tmp_path: Path) -> None:
        store_path = tmp_path / "prov.jsonl"
        store = ProvenanceStore(str(store_path))
        store.append([])
        assert not store_path.exists()


class TestStoreLoad:
    """Test loading records from the store."""

    def test_load_all(self, tmp_path: Path) -> None:
        store_path = tmp_path / "prov.jsonl"
        store = ProvenanceStore(str(store_path))
        original = [make_record(), make_record(file_path="src/utils.py", source="human")]
        store.append(original)
        loaded = store.load_all()
        assert len(loaded) == 2
        assert loaded[0].file_path == "src/main.py"
        assert loaded[0].source == "ai"
        assert loaded[1].source == "human"

    def test_load_empty_store(self, tmp_path: Path) -> None:
        store_path = tmp_path / "prov.jsonl"
        store = ProvenanceStore(str(store_path))
        assert store.load_all() == []

    def test_load_preserves_types(self, tmp_path: Path) -> None:
        store_path = tmp_path / "prov.jsonl"
        store = ProvenanceStore(str(store_path))
        store.append([make_record()])
        loaded = store.load_all()
        assert isinstance(loaded[0].timestamp, datetime)
        assert isinstance(loaded[0].method, ProvenanceSource)
        assert loaded[0].method == ProvenanceSource.GIT_INFER

    def test_load_with_lines_range(self, tmp_path: Path) -> None:
        store_path = tmp_path / "prov.jsonl"
        store = ProvenanceStore(str(store_path))
        record = make_record()
        record.lines_range = (10, 50)
        store.append([record])
        loaded = store.load_all()
        assert loaded[0].lines_range == (10, 50)

    def test_load_skips_corrupt_lines(self, tmp_path: Path) -> None:
        store_path = tmp_path / "prov.jsonl"
        store = ProvenanceStore(str(store_path))
        store.append([make_record()])
        # Corrupt the file by adding invalid JSON
        with open(store_path, "a", encoding="utf-8") as f:
            f.write("NOT JSON\n")
            f.write("{}\n")  # Missing required fields
        loaded = store.load_all()
        assert len(loaded) == 1  # Only the valid record


class TestStoreStats:
    """Test provenance statistics."""

    def test_stats_empty(self, tmp_path: Path) -> None:
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        stats = store.get_stats()
        assert stats["total_files"] == 0
        assert stats["ai_percentage"] == 0.0

    def test_stats_counts(self, tmp_path: Path) -> None:
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        store.append([
            make_record(file_path="a.py", source="ai"),
            make_record(file_path="b.py", source="human", confidence=0.8),
            make_record(file_path="c.py", source="mixed"),
        ])
        stats = store.get_stats()
        assert stats["total_files"] == 3
        assert stats["ai_files"] == 1
        assert stats["human_files"] == 1
        assert stats["mixed_files"] == 1

    def test_stats_deduplicates_by_latest(self, tmp_path: Path) -> None:
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        # First record: ai
        store.append([make_record(
            file_path="a.py",
            source="ai",
            timestamp=datetime(2026, 1, 1),
        )])
        # Later record: human (should win)
        store.append([make_record(
            file_path="a.py",
            source="human",
            timestamp=datetime(2026, 1, 15),
        )])
        stats = store.get_stats()
        assert stats["total_files"] == 1
        assert stats["human_files"] == 1
        assert stats["ai_files"] == 0

    def test_stats_ai_percentage(self, tmp_path: Path) -> None:
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        store.append([
            make_record(file_path="a.py", source="ai"),
            make_record(file_path="b.py", source="ai"),
            make_record(file_path="c.py", source="human", confidence=0.9),
            make_record(file_path="d.py", source="mixed"),
        ])
        stats = store.get_stats()
        # ai_pct = (2 ai + 1 mixed * 0.5) / 4 * 100 = 62.5%
        assert stats["ai_percentage"] == 62.5


class TestGetByFile:
    """Test per-file record lookup."""

    def test_get_by_file(self, tmp_path: Path) -> None:
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        store.append([
            make_record(file_path="a.py"),
            make_record(file_path="b.py"),
            make_record(file_path="a.py", source="human",
                        timestamp=datetime(2026, 2, 1)),
        ])
        records = store.get_by_file("a.py")
        assert len(records) == 2

    def test_get_by_file_not_found(self, tmp_path: Path) -> None:
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        store.append([make_record(file_path="a.py")])
        assert store.get_by_file("nonexistent.py") == []
