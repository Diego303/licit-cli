"""Tests for cryptographic attestation of provenance records."""

from __future__ import annotations

from pathlib import Path

import pytest

from licit.provenance.attestation import ProvenanceAttestor


class TestSignAndVerify:
    """Test HMAC signing and verification."""

    def test_sign_record(self, tmp_path: Path) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        data = {"file_path": "src/main.py", "source": "ai"}
        sig = attestor.sign_record(data)
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA256 hex digest

    def test_verify_valid_signature(self, tmp_path: Path) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        data = {"file_path": "src/main.py", "source": "ai"}
        sig = attestor.sign_record(data)
        assert attestor.verify_record(data, sig)

    def test_verify_tampered_data(self, tmp_path: Path) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        data = {"file_path": "src/main.py", "source": "ai"}
        sig = attestor.sign_record(data)
        data["source"] = "human"  # Tamper
        assert not attestor.verify_record(data, sig)

    def test_verify_wrong_signature(self, tmp_path: Path) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        data = {"file_path": "src/main.py", "source": "ai"}
        assert not attestor.verify_record(data, "wrong" * 16)

    def test_deterministic_signatures(self, tmp_path: Path) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        data = {"file_path": "src/main.py", "source": "ai"}
        sig1 = attestor.sign_record(data)
        sig2 = attestor.sign_record(data)
        assert sig1 == sig2


class TestMerkleTree:
    """Test batch signing with Merkle tree."""

    def test_sign_batch_single(self, tmp_path: Path) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        records = [{"file": "a.py"}]
        root = attestor.sign_batch(records)
        assert isinstance(root, str)
        assert len(root) == 64

    def test_sign_batch_multiple(self, tmp_path: Path) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        records = [{"file": f"file{i}.py"} for i in range(5)]
        root = attestor.sign_batch(records)
        assert isinstance(root, str)
        assert len(root) == 64

    def test_sign_batch_deterministic(self, tmp_path: Path) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        records = [{"file": "a.py"}, {"file": "b.py"}]
        root1 = attestor.sign_batch(records)
        root2 = attestor.sign_batch(records)
        assert root1 == root2

    def test_sign_batch_empty(self, tmp_path: Path) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        assert attestor.sign_batch([]) == ""

    def test_different_records_different_root(self, tmp_path: Path) -> None:
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-key-32-bytes-long-exactly!!")
        attestor = ProvenanceAttestor(str(key_file))
        root1 = attestor.sign_batch([{"file": "a.py"}])
        root2 = attestor.sign_batch([{"file": "b.py"}])
        assert root1 != root2


class TestKeyManagement:
    """Test key loading and generation."""

    def test_load_existing_key(self, tmp_path: Path) -> None:
        key_file = tmp_path / "my.key"
        key_data = b"my-secret-key-for-testing-12345!"
        key_file.write_bytes(key_data)
        attestor = ProvenanceAttestor(str(key_file))
        assert attestor.key == key_data

    def test_generate_key_when_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        attestor = ProvenanceAttestor()
        assert len(attestor.key) == 32
        assert (tmp_path / ".licit" / ".signing-key").exists()

    def test_reuse_generated_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        a1 = ProvenanceAttestor()
        a2 = ProvenanceAttestor()
        assert a1.key == a2.key
