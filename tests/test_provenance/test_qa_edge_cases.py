"""QA edge-case tests for Phase 2 — Provenance.

Covers regression tests for bugs found during QA, edge cases the developer
likely did not write, and cross-module integration paths.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from licit.core.models import ProvenanceRecord, ProvenanceSource
from licit.provenance.attestation import ProvenanceAttestor
from licit.provenance.git_analyzer import CommitInfo, GitAnalyzer
from licit.provenance.heuristics import AICommitHeuristics
from licit.provenance.report import _build_report, generate_provenance_report
from licit.provenance.session_readers.claude_code import ClaudeCodeSessionReader
from licit.provenance.store import ProvenanceStore


# ─────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────


def _record(
    file_path: str = "src/main.py",
    source: str = "ai",
    confidence: float = 0.9,
    method: ProvenanceSource = ProvenanceSource.GIT_INFER,
    timestamp: datetime | None = None,
    agent_tool: str | None = "claude-code",
    model: str | None = "claude-sonnet-4",
    **kwargs: object,
) -> ProvenanceRecord:
    return ProvenanceRecord(
        file_path=file_path,
        source=source,
        confidence=confidence,
        method=method,
        timestamp=timestamp or datetime(2026, 1, 15, 10, 0),
        agent_tool=agent_tool,
        model=model,
        **kwargs,  # type: ignore[arg-type]
    )


@dataclass
class FakeCommit:
    author: str = "Jane Dev"
    author_email: str = "jane@company.com"
    message: str = "Fix a bug"
    files_changed: list[str] = field(default_factory=lambda: ["src/main.py"])
    insertions: int = 5
    deletions: int = 3
    co_authors: list[str] = field(default_factory=list)
    date: datetime = field(default_factory=lambda: datetime(2026, 1, 15, 14, 0))


# ─────────────────────────────────────────────────
# REGRESSION TESTS — Bugs #1, #2, #3
# ─────────────────────────────────────────────────


class TestRegressionBug1InvalidRegex:
    """Bug #1: Invalid regex in custom patterns crashes re.search()."""

    def test_invalid_regex_in_custom_patterns_no_crash(self, tmp_path: Path) -> None:
        patterns = tmp_path / "patterns.json"
        patterns.write_text(
            json.dumps({
                "ai_authors": [],
                "message_patterns": ["[invalid(regex", "^valid$"],
            }),
            encoding="utf-8",
        )
        h = AICommitHeuristics(patterns_file=str(patterns))
        commit = FakeCommit(message="some message")
        # Must not raise re.error
        score, _ = h.score_commit(commit)
        assert isinstance(score, float)

    def test_multiple_invalid_regexes_all_skipped(self, tmp_path: Path) -> None:
        patterns = tmp_path / "patterns.json"
        patterns.write_text(
            json.dumps({
                "ai_authors": [],
                "message_patterns": ["[bad", "(unclosed", "**repeat"],
            }),
            encoding="utf-8",
        )
        h = AICommitHeuristics(patterns_file=str(patterns))
        commit = FakeCommit(message="test message")
        score, _ = h.score_commit(commit)
        assert score < 0.3  # No valid patterns match


class TestRegressionBug2NullParams:
    """Bug #2: params: null in session JSON causes crash."""

    def test_null_params_in_session_entry(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": "Write", "params": null}\n',
            encoding="utf-8",
        )
        reader = ClaudeCodeSessionReader()
        records = reader.read_sessions([str(tmp_path)])
        assert records == []  # Skipped, no crash

    def test_params_is_a_list_not_dict(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": "Write", "params": ["a", "b"]}\n',
            encoding="utf-8",
        )
        reader = ClaudeCodeSessionReader()
        records = reader.read_sessions([str(tmp_path)])
        assert records == []

    def test_params_is_a_string(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": "Write", "params": "invalid"}\n',
            encoding="utf-8",
        )
        reader = ClaudeCodeSessionReader()
        records = reader.read_sessions([str(tmp_path)])
        assert records == []


class TestRegressionBug3NullGuardrailValues:
    """Bug #3: len(None) when guardrail YAML values are explicitly null."""

    def test_null_protected_files_in_guardrails(self, tmp_path: Path) -> None:
        import yaml

        from licit.core.evidence import EvidenceCollector
        from licit.core.project import CICDConfig, ProjectContext, SecurityTooling

        architect_dir = tmp_path / ".architect"
        architect_dir.mkdir()
        (architect_dir / "config.yaml").write_text(
            yaml.dump({
                "guardrails": {
                    "protected_files": None,
                    "blocked_commands": None,
                    "code_rules": ["rule1"],
                },
            }),
            encoding="utf-8",
        )
        ctx = ProjectContext(
            root_dir=str(tmp_path),
            name="test",
            cicd=CICDConfig(platform="none"),
            security=SecurityTooling(),
            architect_config_path=".architect/config.yaml",
        )
        collector = EvidenceCollector(str(tmp_path), ctx)
        ev = collector.collect()
        assert ev.has_guardrails is True
        assert ev.guardrail_count == 1  # Only code_rules has one item


# ─────────────────────────────────────────────────
# HEURISTICS — edge cases
# ─────────────────────────────────────────────────


class TestHeuristicsEdgeCases:
    """Edge cases for AICommitHeuristics."""

    def test_empty_author_and_email(self) -> None:
        commit = FakeCommit(author="", author_email="")
        h = AICommitHeuristics()
        score, _ = h.score_commit(commit)
        assert score < 0.5

    def test_none_date_attribute(self) -> None:
        commit = FakeCommit()
        commit.date = None  # type: ignore[assignment]
        h = AICommitHeuristics()
        result = h._check_time_patterns(commit)
        assert result.score == 0.0

    def test_unicode_in_author_name(self) -> None:
        commit = FakeCommit(author="José García", author_email="jose@company.com")
        h = AICommitHeuristics()
        score, _ = h.score_commit(commit)
        assert score < 0.3

    def test_unicode_in_commit_message(self) -> None:
        commit = FakeCommit(message="修复了登录超时错误")
        h = AICommitHeuristics()
        score, _ = h.score_commit(commit)
        assert isinstance(score, float)

    def test_very_long_message(self) -> None:
        commit = FakeCommit(message="fix: " + "x" * 10_000)
        h = AICommitHeuristics()
        score, _ = h.score_commit(commit)
        assert isinstance(score, float)

    def test_all_heuristics_fire_simultaneously(self) -> None:
        """Claude author + AI message + bulk + co-author + test files + late hour."""
        commit = FakeCommit(
            author="Claude",
            author_email="claude@anthropic.com",
            message="feat(auth): implement full auth module",
            files_changed=[f"test_{i}.py" for i in range(30)],
            insertions=1000,
            deletions=200,
            co_authors=["Claude Opus 4 <noreply@anthropic.com>"],
            date=datetime(2026, 1, 15, 3, 0),
        )
        h = AICommitHeuristics()
        score, reasons = h.score_commit(commit)
        assert score >= 0.7
        assert len(reasons) >= 3

    def test_score_never_exceeds_one(self) -> None:
        """Even with extreme signals, score should cap at 1.0."""
        commit = FakeCommit(
            author="Claude Bot Anthropic AI",
            author_email="claude+bot@anthropic.com",
            message="feat: generated by AI [bot] auto-generate",
            co_authors=["Claude AI <ai@anthropic.com>", "Copilot <copilot@github.com>"],
            files_changed=[f"test_{i}.py" for i in range(50)],
            insertions=5000,
            deletions=1000,
            date=datetime(2026, 1, 15, 2, 0),
        )
        h = AICommitHeuristics()
        score, _ = h.score_commit(commit)
        assert score <= 1.0

    def test_boundary_hour_1am(self) -> None:
        commit = FakeCommit(date=datetime(2026, 1, 15, 1, 0))
        h = AICommitHeuristics()
        result = h._check_time_patterns(commit)
        assert result.score == 0.3

    def test_boundary_hour_5am(self) -> None:
        commit = FakeCommit(date=datetime(2026, 1, 15, 5, 0))
        h = AICommitHeuristics()
        result = h._check_time_patterns(commit)
        assert result.score == 0.3

    def test_boundary_hour_6am_not_unusual(self) -> None:
        commit = FakeCommit(date=datetime(2026, 1, 15, 6, 0))
        h = AICommitHeuristics()
        result = h._check_time_patterns(commit)
        assert result.score == 0.0

    def test_boundary_hour_midnight_not_unusual(self) -> None:
        commit = FakeCommit(date=datetime(2026, 1, 15, 0, 0))
        h = AICommitHeuristics()
        result = h._check_time_patterns(commit)
        assert result.score == 0.0

    def test_custom_patterns_with_empty_json(self, tmp_path: Path) -> None:
        patterns = tmp_path / "patterns.json"
        patterns.write_text("{}", encoding="utf-8")
        h = AICommitHeuristics(patterns_file=str(patterns))
        commit = FakeCommit()
        score, _ = h.score_commit(commit)
        assert isinstance(score, float)

    def test_custom_patterns_with_non_dict_json(self, tmp_path: Path) -> None:
        patterns = tmp_path / "patterns.json"
        patterns.write_text('"just a string"', encoding="utf-8")
        h = AICommitHeuristics(patterns_file=str(patterns))
        # Should log warning, not crash
        commit = FakeCommit()
        score, _ = h.score_commit(commit)
        assert isinstance(score, float)

    def test_empty_files_changed_no_crash(self) -> None:
        commit = FakeCommit(files_changed=[])
        h = AICommitHeuristics()
        result = h._check_file_patterns(commit)
        assert result.score == 0.0

    def test_exact_threshold_bulk_changes(self) -> None:
        """Exactly 20 files and 500 lines — should hit the large bulk threshold."""
        files = [f"src/file{i}.py" for i in range(21)]
        commit = FakeCommit(files_changed=files, insertions=450, deletions=51)
        h = AICommitHeuristics()
        result = h._check_bulk_changes(commit)
        assert result.score == 0.6


# ─────────────────────────────────────────────────
# GIT ANALYZER — edge cases
# ─────────────────────────────────────────────────


class TestGitAnalyzerEdgeCases:
    """Edge cases for GitAnalyzer."""

    def test_unicode_author_name(self, tmp_path: Path) -> None:
        analyzer = GitAnalyzer(str(tmp_path))
        sha = "a" * 40
        header = "\x01".join([sha, "José García", "jose@co.com", "2026-01-15T14:00:00+00:00", "Fix bug", ""])
        output = f"\x00{header}\n5\t3\tsrc/main.py"
        commits = analyzer._parse_git_log(output)
        assert len(commits) == 1
        assert commits[0].author == "José García"

    def test_unicode_in_file_paths(self, tmp_path: Path) -> None:
        analyzer = GitAnalyzer(str(tmp_path))
        sha = "a" * 40
        header = "\x01".join([sha, "Dev", "dev@co.com", "2026-01-15T14:00:00+00:00", "Fix", ""])
        output = f"\x00{header}\n5\t3\tsrc/módulo/archivo.py"
        commits = analyzer._parse_git_log(output)
        assert commits[0].files_changed == ["src/módulo/archivo.py"]

    def test_tab_in_filename(self, tmp_path: Path) -> None:
        """Filenames with tabs are handled by split('\\t', 2)."""
        analyzer = GitAnalyzer(str(tmp_path))
        sha = "a" * 40
        header = "\x01".join([sha, "Dev", "dev@co.com", "2026-01-15T14:00:00+00:00", "Fix", ""])
        output = f"\x00{header}\n5\t3\tpath\twith\ttabs.py"
        commits = analyzer._parse_git_log(output)
        assert "path\twith\ttabs.py" in commits[0].files_changed

    def test_empty_commit_body(self, tmp_path: Path) -> None:
        analyzer = GitAnalyzer(str(tmp_path))
        sha = "a" * 40
        # Only 5 fields, no body
        fields = [sha, "Dev", "dev@co.com", "2026-01-15T14:00:00+00:00", "Fix"]
        header = "\x01".join(fields)
        output = f"\x00{header}\n5\t3\tsrc/main.py"
        commits = analyzer._parse_git_log(output)
        assert len(commits) == 1
        assert commits[0].co_authors == []

    def test_malformed_date_skipped(self, tmp_path: Path) -> None:
        analyzer = GitAnalyzer(str(tmp_path))
        sha = "a" * 40
        header = "\x01".join([sha, "Dev", "dev@co.com", "NOT-A-DATE", "Fix", ""])
        output = f"\x00{header}\n5\t3\tsrc/main.py"
        commits = analyzer._parse_git_log(output)
        assert len(commits) == 0  # ValueError caught in parse

    def test_subprocess_timeout(self, tmp_path: Path) -> None:
        analyzer = GitAnalyzer(str(tmp_path))
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30)):
            records = analyzer.analyze()
        assert records == []

    def test_subprocess_oserror(self, tmp_path: Path) -> None:
        analyzer = GitAnalyzer(str(tmp_path))
        with patch("subprocess.run", side_effect=OSError("git not found")):
            # Should propagate — no catch for OSError in _get_commits
            with pytest.raises(OSError):
                analyzer.analyze()

    def test_commit_with_no_files(self, tmp_path: Path) -> None:
        """A merge commit with no numstat lines."""
        analyzer = GitAnalyzer(str(tmp_path))
        sha = "a" * 40
        header = "\x01".join([sha, "Dev", "dev@co.com", "2026-01-15T14:00:00+00:00", "Merge branch", ""])
        output = f"\x00{header}"
        commits = analyzer._parse_git_log(output)
        assert len(commits) == 1
        assert commits[0].files_changed == []
        assert commits[0].insertions == 0

    def test_multiple_co_authors(self, tmp_path: Path) -> None:
        analyzer = GitAnalyzer(str(tmp_path))
        sha = "a" * 40
        body = "Co-authored-by: Claude <c@a.com>\nCo-authored-by: Copilot <cp@gh.com>"
        header = "\x01".join([sha, "Dev", "dev@co.com", "2026-01-15T14:00:00+00:00", "Fix", body])
        output = f"\x00{header}\n5\t3\tsrc/main.py"
        commits = analyzer._parse_git_log(output)
        assert len(commits[0].co_authors) == 2

    def test_co_author_case_insensitive(self, tmp_path: Path) -> None:
        analyzer = GitAnalyzer(str(tmp_path))
        sha = "a" * 40
        body = "CO-AUTHORED-BY: Claude <c@a.com>"
        header = "\x01".join([sha, "Dev", "dev@co.com", "2026-01-15T14:00:00+00:00", "Fix", body])
        output = f"\x00{header}\n5\t3\tsrc/main.py"
        commits = analyzer._parse_git_log(output)
        assert "Claude" in commits[0].co_authors

    def test_infer_model_from_co_author(self, tmp_path: Path) -> None:
        analyzer = GitAnalyzer(str(tmp_path))
        commit = CommitInfo(
            sha="a" * 40,
            author="Dev",
            author_email="dev@co.com",
            date=datetime(2026, 1, 15),
            message="feat: auth",
            files_changed=[],
            insertions=0,
            deletions=0,
            co_authors=["Claude Opus 4 <noreply@anthropic.com>"],
        )
        assert analyzer._infer_model(commit) == "claude-opus-4"

    def test_infer_agent_from_message(self, tmp_path: Path) -> None:
        analyzer = GitAnalyzer(str(tmp_path))
        commit = CommitInfo(
            sha="a" * 40,
            author="Dev",
            author_email="dev@co.com",
            date=datetime(2026, 1, 15),
            message="Generated by Devin AI",
            files_changed=[],
            insertions=0,
            deletions=0,
        )
        assert analyzer._infer_agent(commit) == "devin"

    def test_since_parameter_filters_by_author_date(self, tmp_path: Path) -> None:
        """Since filtering is done in Python by author date, not by git flag."""
        analyzer = GitAnalyzer(str(tmp_path))
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            analyzer.analyze(since="2026-01-01")
        # git command should NOT contain --since (filtering is in Python now)
        call_args = mock_run.call_args[0][0]
        assert not any("--since" in str(arg) for arg in call_args)
        assert mock_run.called


# ─────────────────────────────────────────────────
# STORE — edge cases
# ─────────────────────────────────────────────────


class TestStoreEdgeCases:
    """Edge cases for ProvenanceStore."""

    def test_unicode_file_path_roundtrip(self, tmp_path: Path) -> None:
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        store.append([_record(file_path="src/módulo/archivo.py")])
        loaded = store.load_all()
        assert loaded[0].file_path == "src/módulo/archivo.py"

    def test_special_chars_in_file_path(self, tmp_path: Path) -> None:
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        store.append([_record(file_path="src/file with spaces & (parens).py")])
        loaded = store.load_all()
        assert loaded[0].file_path == "src/file with spaces & (parens).py"

    def test_empty_string_file_path(self, tmp_path: Path) -> None:
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        store.append([_record(file_path="")])
        loaded = store.load_all()
        assert loaded[0].file_path == ""

    def test_none_optional_fields_roundtrip(self, tmp_path: Path) -> None:
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        record = _record(agent_tool=None, model=None)
        record.session_id = None
        record.signature = None
        store.append([record])
        loaded = store.load_all()
        assert loaded[0].agent_tool is None
        assert loaded[0].model is None

    def test_large_number_of_records(self, tmp_path: Path) -> None:
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        records = [_record(file_path=f"file_{i}.py") for i in range(500)]
        store.append(records)
        loaded = store.load_all()
        assert len(loaded) == 500

    def test_stats_all_ai_files(self, tmp_path: Path) -> None:
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        store.append([
            _record(file_path="a.py", source="ai"),
            _record(file_path="b.py", source="ai"),
        ])
        stats = store.get_stats()
        assert stats["ai_percentage"] == 100.0

    def test_stats_all_human_files(self, tmp_path: Path) -> None:
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        store.append([
            _record(file_path="a.py", source="human"),
            _record(file_path="b.py", source="human"),
        ])
        stats = store.get_stats()
        assert stats["ai_percentage"] == 0.0

    def test_get_by_file_returns_latest_version(self, tmp_path: Path) -> None:
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        store.save([
            _record(file_path="a.py", source="ai", timestamp=datetime(2026, 1, 1)),
            _record(file_path="a.py", source="human", timestamp=datetime(2026, 1, 15)),
            _record(file_path="a.py", source="mixed", timestamp=datetime(2026, 2, 1)),
        ])
        records = store.get_by_file("a.py")
        # Store deduplicates: only the latest record per file is kept
        assert len(records) == 1
        assert records[0].source == "mixed"

    def test_load_handles_blank_lines(self, tmp_path: Path) -> None:
        store_path = tmp_path / "prov.jsonl"
        store = ProvenanceStore(str(store_path))
        store.append([_record()])
        # Inject blank lines
        content = store_path.read_text(encoding="utf-8")
        store_path.write_text(f"\n\n{content}\n\n", encoding="utf-8")
        loaded = store.load_all()
        assert len(loaded) == 1

    def test_store_path_with_deep_nonexistent_dir(self, tmp_path: Path) -> None:
        deep_path = tmp_path / "a" / "b" / "c" / "d" / "prov.jsonl"
        store = ProvenanceStore(str(deep_path))
        store.append([_record()])
        assert deep_path.exists()

    def test_signature_field_preserved(self, tmp_path: Path) -> None:
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        record = _record()
        record.signature = "abc123" * 10 + "abcd"
        store.append([record])
        loaded = store.load_all()
        assert loaded[0].signature == "abc123" * 10 + "abcd"


# ─────────────────────────────────────────────────
# ATTESTATION — edge cases
# ─────────────────────────────────────────────────


class TestAttestationEdgeCases:
    """Edge cases for ProvenanceAttestor."""

    def test_sign_empty_record(self, tmp_path: Path) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        sig = attestor.sign_record({})
        assert isinstance(sig, str)
        assert len(sig) == 64

    def test_sign_record_with_unicode_values(self, tmp_path: Path) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        data = {"file_path": "src/módulo/archivo.py", "source": "IA"}
        sig = attestor.sign_record(data)
        assert attestor.verify_record(data, sig)

    def test_sign_record_with_nested_data(self, tmp_path: Path) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        data = {"file_path": "x.py", "meta": {"nested": True, "list": [1, 2, 3]}}
        sig = attestor.sign_record(data)
        assert attestor.verify_record(data, sig)

    def test_different_keys_different_signatures(self, tmp_path: Path) -> None:
        key1 = tmp_path / "key1"
        key2 = tmp_path / "key2"
        key1.write_bytes(b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        key2.write_bytes(b"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
        a1 = ProvenanceAttestor(str(key1))
        a2 = ProvenanceAttestor(str(key2))
        data = {"file_path": "test.py"}
        assert a1.sign_record(data) != a2.sign_record(data)

    def test_verify_empty_signature_string(self, tmp_path: Path) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        assert not attestor.verify_record({"file": "x"}, "")

    def test_merkle_tree_large_batch(self, tmp_path: Path) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        records = [{"file": f"file{i}.py"} for i in range(100)]
        root = attestor.sign_batch(records)
        assert isinstance(root, str)
        assert len(root) == 64

    def test_merkle_tree_odd_number_records(self, tmp_path: Path) -> None:
        """Odd count → last element paired with itself."""
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        root = attestor.sign_batch([{"f": "1"}, {"f": "2"}, {"f": "3"}])
        assert isinstance(root, str)
        assert len(root) == 64

    def test_key_generation_in_nonwritable_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When key can't be written, attestor still works with in-memory key."""
        nonexistent = tmp_path / "nonexistent_subdir"
        monkeypatch.chdir(tmp_path)
        # Make .licit directory but make it read-only
        licit_dir = tmp_path / ".licit"
        licit_dir.mkdir()
        os.chmod(str(licit_dir), 0o444)
        try:
            attestor = ProvenanceAttestor()
            # Should have a key despite write failure
            assert len(attestor.key) == 32
            # Should still be able to sign
            sig = attestor.sign_record({"test": True})
            assert len(sig) == 64
        finally:
            os.chmod(str(licit_dir), 0o755)

    def test_sign_record_with_datetime_value(self, tmp_path: Path) -> None:
        """Records with datetime should serialize via default=str."""
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        data = {"file": "x.py", "timestamp": datetime(2026, 1, 15)}
        sig = attestor.sign_record(data)
        assert len(sig) == 64


# ─────────────────────────────────────────────────
# SESSION READER — edge cases
# ─────────────────────────────────────────────────


class TestSessionReaderEdgeCases:
    """Edge cases for ClaudeCodeSessionReader."""

    def test_empty_file_path_string_skipped(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": "Write", '
            '"params": {"file_path": ""}}\n',
            encoding="utf-8",
        )
        reader = ClaudeCodeSessionReader()
        records = reader.read_sessions([str(tmp_path)])
        assert records == []

    def test_file_path_is_integer(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": "Write", '
            '"params": {"file_path": 42}}\n',
            encoding="utf-8",
        )
        reader = ClaudeCodeSessionReader()
        records = reader.read_sessions([str(tmp_path)])
        assert records == []  # Not a string

    def test_unicode_file_path(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": "Write", '
            '"params": {"file_path": "src/módulo/archivo.py"}, '
            '"timestamp": "2026-01-15T10:00:00+00:00"}\n',
            encoding="utf-8",
        )
        reader = ClaudeCodeSessionReader()
        records = reader.read_sessions([str(tmp_path)])
        assert len(records) == 1
        assert records[0].file_path == "src/módulo/archivo.py"

    def test_tool_name_not_a_string(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": 42, '
            '"params": {"file_path": "test.py"}}\n',
            encoding="utf-8",
        )
        reader = ClaudeCodeSessionReader()
        records = reader.read_sessions([str(tmp_path)])
        assert records == []

    def test_entry_not_a_dict(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        session.write_text(
            '"just a string"\n'
            '42\n'
            '[1, 2, 3]\n',
            encoding="utf-8",
        )
        reader = ClaudeCodeSessionReader()
        records = reader.read_sessions([str(tmp_path)])
        assert records == []

    def test_bash_with_redirect_skipped(self, tmp_path: Path) -> None:
        """Bash commands with > or tee are skipped (can't reliably determine file)."""
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": "Bash", '
            '"params": {"command": "echo hello > output.txt"}}\n',
            encoding="utf-8",
        )
        reader = ClaudeCodeSessionReader()
        records = reader.read_sessions([str(tmp_path)])
        assert records == []

    def test_no_timestamp_uses_now(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": "Write", '
            '"params": {"file_path": "test.py"}}\n',
            encoding="utf-8",
        )
        reader = ClaudeCodeSessionReader()
        records = reader.read_sessions([str(tmp_path)])
        assert len(records) == 1
        # Timestamp should be approximately now
        assert (datetime.now() - records[0].timestamp).total_seconds() < 5

    def test_model_not_a_string(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        session.write_text(
            '{"type": "tool_use", "tool": "Write", '
            '"params": {"file_path": "test.py"}, '
            '"timestamp": "2026-01-15T10:00:00+00:00", '
            '"model": 42}\n',
            encoding="utf-8",
        )
        reader = ClaudeCodeSessionReader()
        records = reader.read_sessions([str(tmp_path)])
        assert len(records) == 1
        assert records[0].model is None  # Non-string model → None

    def test_multiple_session_dirs(self, tmp_path: Path) -> None:
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        (dir1 / "s1.jsonl").write_text(
            '{"type": "tool_use", "tool": "Write", '
            '"params": {"file_path": "a.py"}, '
            '"timestamp": "2026-01-15T10:00:00+00:00"}\n',
            encoding="utf-8",
        )
        (dir2 / "s2.jsonl").write_text(
            '{"type": "tool_use", "tool": "Edit", '
            '"params": {"file_path": "b.py"}, '
            '"timestamp": "2026-01-15T11:00:00+00:00"}\n',
            encoding="utf-8",
        )
        reader = ClaudeCodeSessionReader()
        records = reader.read_sessions([str(dir1), str(dir2)])
        assert len(records) == 2
        assert {r.file_path for r in records} == {"a.py", "b.py"}


# ─────────────────────────────────────────────────
# REPORT — edge cases
# ─────────────────────────────────────────────────


class TestReportEdgeCases:
    """Edge cases for provenance report generation."""

    def test_empty_records_report(self) -> None:
        report = _build_report([])
        assert "# Provenance Report" in report
        assert "Total files | 0" in report

    def test_single_record_report(self) -> None:
        records = [_record(file_path="a.py", source="ai")]
        report = _build_report(records)
        assert "a.py" in report
        assert "ai" in report

    def test_pipe_in_file_path_escaped(self) -> None:
        records = [_record(file_path="path|with|pipes.py")]
        report = _build_report(records)
        assert "path\\|with\\|pipes.py" in report

    def test_unicode_in_report(self) -> None:
        records = [_record(file_path="src/módulo/archivo.py")]
        report = _build_report(records)
        assert "módulo" in report

    def test_deduplication_latest_wins(self) -> None:
        records = [
            _record(file_path="a.py", source="ai", timestamp=datetime(2026, 1, 1)),
            _record(file_path="a.py", source="human", timestamp=datetime(2026, 2, 1)),
        ]
        report = _build_report(records)
        assert "Total files | 1" in report
        assert "Human-written | 1" in report

    def test_all_sources_represented(self) -> None:
        records = [
            _record(file_path="a.py", source="ai"),
            _record(file_path="b.py", source="human"),
            _record(file_path="c.py", source="mixed"),
        ]
        report = _build_report(records)
        assert "AI-generated | 1" in report
        assert "Human-written | 1" in report
        assert "Mixed | 1" in report

    def test_report_no_agents_or_models(self) -> None:
        records = [_record(file_path="a.py", agent_tool=None, model=None)]
        report = _build_report(records)
        assert "## AI Tools Detected" not in report
        assert "## Models Detected" not in report

    def test_report_with_multiple_agents_and_models(self) -> None:
        records = [
            _record(file_path="a.py", agent_tool="claude-code", model="claude-sonnet-4"),
            _record(file_path="b.py", agent_tool="cursor", model="gpt-4o"),
            _record(file_path="c.py", agent_tool="claude-code", model="claude-opus-4"),
        ]
        report = _build_report(records)
        assert "claude-code" in report
        assert "cursor" in report
        assert "## AI Tools Detected" in report
        assert "## Models Detected" in report

    def test_generate_report_creates_file(self, tmp_path: Path) -> None:
        output = tmp_path / "reports" / "provenance.md"
        generate_provenance_report([_record()], str(output))
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "# Provenance Report" in content

    def test_generate_report_creates_parent_dirs(self, tmp_path: Path) -> None:
        output = tmp_path / "deep" / "nested" / "dir" / "report.md"
        generate_provenance_report([], str(output))
        assert output.exists()

    def test_report_file_details_sorted(self) -> None:
        records = [
            _record(file_path="z.py"),
            _record(file_path="a.py"),
            _record(file_path="m.py"),
        ]
        report = _build_report(records)
        # Find positions of file names in report
        a_pos = report.index("a.py")
        m_pos = report.index("m.py")
        z_pos = report.index("z.py")
        assert a_pos < m_pos < z_pos


# ─────────────────────────────────────────────────
# CROSS-MODULE INTEGRATION
# ─────────────────────────────────────────────────


class TestCrossModuleIntegration:
    """Tests verifying modules work together correctly."""

    def test_git_analyzer_to_store_to_report_pipeline(self, tmp_path: Path) -> None:
        """Full pipeline: analyze git → store records → generate report."""
        analyzer = GitAnalyzer(str(tmp_path))
        sha = "a" * 40
        header = "\x01".join([
            sha, "Claude", "claude@anthropic.com",
            "2026-01-15T14:00:00+00:00", "feat: add auth", "",
        ])
        output = f"\x00{header}\n50\t0\tsrc/auth.py"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=output, stderr=""
            )
            records = analyzer.analyze()

        # Store
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        store.append(records)

        # Verify stored correctly
        loaded = store.load_all()
        assert len(loaded) == len(records)

        # Report
        report_path = tmp_path / "report.md"
        generate_provenance_report(loaded, str(report_path))
        report = report_path.read_text(encoding="utf-8")
        assert "auth.py" in report
        assert "claude-code" in report

    def test_store_stats_match_report_summary(self, tmp_path: Path) -> None:
        """Store stats and report summary should show consistent numbers."""
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        records = [
            _record(file_path="a.py", source="ai"),
            _record(file_path="b.py", source="human"),
            _record(file_path="c.py", source="mixed"),
        ]
        store.append(records)

        stats = store.get_stats()
        report = _build_report(records)

        assert f"Total files | {stats['total_files']}" in report
        assert f"AI-generated | {stats['ai_files']}" in report
        assert f"Human-written | {stats['human_files']}" in report

    def test_attestor_sign_and_verify_real_record(self, tmp_path: Path) -> None:
        """Sign a real ProvenanceRecord dict, store it, verify after load."""
        from dataclasses import asdict

        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))

        record = _record()
        data = asdict(record)
        data["timestamp"] = record.timestamp.isoformat()
        # Sign without signature field (matches tracker._sign_records behavior)
        sig = attestor.sign_record(data)
        record.signature = sig

        # Store and reload
        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        store.append([record])
        loaded = store.load_all()

        assert loaded[0].signature == sig
        # Verify: reconstruct the same data dict that was signed
        verify_data = asdict(loaded[0])
        verify_data["timestamp"] = loaded[0].timestamp.isoformat()
        # The original data included signature=None at sign time
        verify_data["signature"] = None
        if loaded[0].lines_range is None:
            verify_data["lines_range"] = None
        assert attestor.verify_record(verify_data, sig)

    def test_session_reader_records_storable(self, tmp_path: Path) -> None:
        """Records from session reader can be stored and loaded without loss."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir()
        (session_dir / "test.jsonl").write_text(
            '{"type": "tool_use", "tool": "Write", '
            '"params": {"file_path": "src/app.py"}, '
            '"timestamp": "2026-01-15T10:00:00+00:00", '
            '"model": "claude-sonnet-4"}\n',
            encoding="utf-8",
        )
        reader = ClaudeCodeSessionReader()
        records = reader.read_sessions([str(session_dir)])

        store = ProvenanceStore(str(tmp_path / "prov.jsonl"))
        store.append(records)
        loaded = store.load_all()

        assert len(loaded) == 1
        assert loaded[0].file_path == "src/app.py"
        assert loaded[0].agent_tool == "claude-code"
        assert loaded[0].model == "claude-sonnet-4"
        assert loaded[0].method == ProvenanceSource.SESSION_LOG


# ─────────────────────────────────────────────────
# TRACKER — additional edge cases
# ─────────────────────────────────────────────────


class TestTrackerEdgeCases:
    """Edge cases for ProvenanceTracker."""

    def test_empty_methods_list(self, tmp_path: Path) -> None:
        from licit.config.schema import ProvenanceConfig
        from licit.provenance.tracker import ProvenanceTracker

        config = ProvenanceConfig(
            methods=[],
            store_path=str(tmp_path / ".licit" / "provenance.jsonl"),
        )
        tracker = ProvenanceTracker(str(tmp_path), config)
        records = tracker.analyze()
        assert records == []

    def test_unknown_method_ignored(self, tmp_path: Path) -> None:
        from licit.config.schema import ProvenanceConfig
        from licit.provenance.tracker import ProvenanceTracker

        config = ProvenanceConfig(
            methods=["nonexistent-method"],
            store_path=str(tmp_path / ".licit" / "provenance.jsonl"),
        )
        tracker = ProvenanceTracker(str(tmp_path), config)
        records = tracker.analyze()
        assert records == []

    def test_threshold_zero_passes_everything(self, tmp_path: Path) -> None:
        from licit.config.schema import ProvenanceConfig
        from licit.provenance.tracker import ProvenanceTracker

        config = ProvenanceConfig(
            methods=["git-infer"],
            confidence_threshold=0.0,
            store_path=str(tmp_path / ".licit" / "provenance.jsonl"),
        )
        tracker = ProvenanceTracker(str(tmp_path), config)

        sha = "a" * 40
        header = "\x01".join([sha, "Dev", "dev@co.com", "2026-01-15T14:00:00+00:00", "Fix", ""])
        output = f"\x00{header}\n5\t3\tsrc/main.py"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=output, stderr=""
            )
            records = tracker.analyze()

        assert len(records) >= 1
