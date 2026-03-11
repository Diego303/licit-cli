"""Cryptographic signing of provenance records for tamper evidence."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path

import structlog

logger = structlog.get_logger()


class ProvenanceAttestor:
    """Signs provenance records with HMAC-SHA256 for integrity verification.

    Uses a project-local signing key stored in .licit/.signing-key.
    In V1 this will support proper key management (Sigstore/cosign).
    """

    def __init__(self, key_path: str | None = None) -> None:
        self.key = self._load_or_generate_key(key_path)

    def sign_record(self, record_data: dict[str, object]) -> str:
        """Generate HMAC-SHA256 signature for a provenance record."""
        canonical = json.dumps(record_data, sort_keys=True, default=str)
        return hmac.new(
            self.key, canonical.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def verify_record(self, record_data: dict[str, object], signature: str) -> bool:
        """Verify HMAC signature of a provenance record."""
        expected = self.sign_record(record_data)
        return hmac.compare_digest(expected, signature)

    def sign_batch(self, records: list[dict[str, object]]) -> str:
        """Generate a Merkle root hash for a batch of records.

        Returns empty string for empty input.
        """
        if not records:
            return ""

        hashes: list[str] = []
        for record in records:
            canonical = json.dumps(record, sort_keys=True, default=str)
            hashes.append(hashlib.sha256(canonical.encode("utf-8")).hexdigest())

        # Build simple Merkle tree
        while len(hashes) > 1:
            new_level: list[str] = []
            for i in range(0, len(hashes), 2):
                left = hashes[i]
                right = hashes[i + 1] if i + 1 < len(hashes) else hashes[i]
                combined = left + right
                new_level.append(hashlib.sha256(combined.encode("utf-8")).hexdigest())
            hashes = new_level

        return hashes[0]

    def _load_or_generate_key(self, path: str | None) -> bytes:
        """Load signing key from file, or generate and persist a new one."""
        # Try user-specified path first
        if path:
            p = Path(path)
            try:
                if p.exists():
                    logger.info("signing_key_loaded", path=path)
                    return p.read_bytes()
            except OSError as exc:
                logger.warning("signing_key_read_error", path=path, error=str(exc))
            logger.warning("signing_key_not_found", path=path)

        # Fall back to project-local key
        key_file = Path(".licit/.signing-key")
        try:
            if key_file.exists():
                return key_file.read_bytes()
        except OSError as exc:
            logger.warning("signing_key_read_error", path=str(key_file), error=str(exc))

        # Generate new key
        key = os.urandom(32)
        try:
            key_file.parent.mkdir(parents=True, exist_ok=True)
            key_file.write_bytes(key)
            logger.info("signing_key_generated", path=str(key_file))
        except OSError as exc:
            logger.warning("signing_key_write_error", path=str(key_file), error=str(exc))
        return key
