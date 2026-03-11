"""Base protocol for agent session readers."""

from __future__ import annotations

from typing import Protocol

from licit.core.models import ProvenanceRecord


class SessionReader(Protocol):
    """Protocol that all agent session readers must implement.

    A session reader parses session logs from a specific AI coding tool
    and extracts provenance records for files created or modified.
    """

    @property
    def agent_name(self) -> str:
        """Name of the agent tool this reader handles (e.g. 'claude-code')."""
        ...

    def read_sessions(self, session_dirs: list[str]) -> list[ProvenanceRecord]:
        """Read session logs and return provenance records.

        Args:
            session_dirs: Directories to search for session files.

        Returns:
            List of provenance records extracted from sessions.
        """
        ...
