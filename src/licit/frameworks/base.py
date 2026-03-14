"""Base protocol for compliance frameworks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from licit.core.evidence import EvidenceBundle
    from licit.core.models import ControlRequirement, ControlResult
    from licit.core.project import ProjectContext


@runtime_checkable
class ComplianceFramework(Protocol):
    """Protocol that all compliance frameworks must implement.

    Frameworks evaluate a project's compliance posture against a set of
    regulatory requirements using evidence collected from the project.
    """

    @property
    def name(self) -> str:
        """Unique framework identifier (e.g. 'eu-ai-act')."""
        ...

    @property
    def version(self) -> str:
        """Framework version (e.g. '2024/1689')."""
        ...

    @property
    def description(self) -> str:
        """Human-readable framework description."""
        ...

    def get_requirements(self) -> list[ControlRequirement]:
        """Return all evaluable requirements for this framework."""
        ...

    def evaluate(
        self,
        context: ProjectContext,
        evidence: EvidenceBundle,
    ) -> list[ControlResult]:
        """Evaluate project compliance against all requirements."""
        ...
