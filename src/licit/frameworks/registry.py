"""Framework registry for managing compliance frameworks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from licit.frameworks.base import ComplianceFramework

logger = structlog.get_logger()


class FrameworkRegistry:
    """Registry of available compliance frameworks."""

    def __init__(self) -> None:
        self._frameworks: dict[str, ComplianceFramework] = {}

    def register(self, framework: ComplianceFramework) -> None:
        """Register a compliance framework."""
        self._frameworks[framework.name] = framework
        logger.info(
            "framework_registered",
            name=framework.name,
            version=framework.version,
        )

    def get(self, name: str) -> ComplianceFramework | None:
        """Get a framework by name."""
        return self._frameworks.get(name)

    def list_all(self) -> list[ComplianceFramework]:
        """Return all registered frameworks."""
        return list(self._frameworks.values())

    def names(self) -> list[str]:
        """Return names of all registered frameworks."""
        return list(self._frameworks.keys())


# Global registry instance
_registry = FrameworkRegistry()


def get_registry() -> FrameworkRegistry:
    """Get the global framework registry."""
    return _registry
