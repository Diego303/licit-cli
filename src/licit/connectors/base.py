"""Base protocol for licit connectors.

Connectors are optional integrations with external tools that enrich
the evidence bundle used for compliance evaluation. Each connector reads
data from a specific tool's output (reports, SARIF, audit logs) and
contributes findings to the EvidenceBundle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from licit.core.evidence import EvidenceBundle


@dataclass
class ConnectorResult:
    """Result of a connector read operation."""

    connector_name: str
    files_read: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """A connector succeeded if it read at least one file with no errors."""
        return self.files_read > 0 and len(self.errors) == 0

    @property
    def has_errors(self) -> bool:
        """Whether any errors occurred during collection."""
        return len(self.errors) > 0


@runtime_checkable
class Connector(Protocol):
    """Protocol that all connectors must implement.

    Connectors read data from external tool outputs and enrich
    the EvidenceBundle with their findings.
    """

    @property
    def name(self) -> str:
        """Unique connector identifier (e.g. 'architect', 'vigil')."""
        ...

    @property
    def enabled(self) -> bool:
        """Whether this connector is currently enabled."""
        ...

    def available(self) -> bool:
        """Check whether the connector's data sources exist on disk."""
        ...

    def collect(self, evidence: EvidenceBundle) -> ConnectorResult:
        """Read external tool data and enrich the evidence bundle.

        Mutates ``evidence`` in-place and returns a summary of what was read.
        """
        ...
