"""Core data models for licit compliance evaluation."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class ComplianceStatus(StrEnum):
    """Status of a compliance control evaluation."""

    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non-compliant"
    NOT_APPLICABLE = "n/a"
    NOT_EVALUATED = "not-evaluated"


class ChangeSeverity(StrEnum):
    """Severity of an agent config change."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class ProvenanceSource(StrEnum):
    """How provenance was determined."""

    GIT_INFER = "git-infer"
    SESSION_LOG = "session-log"
    GIT_AI = "git-ai"
    MANUAL = "manual"
    CONNECTOR = "connector"


@dataclass
class ProvenanceRecord:
    """A single provenance record for a file or range of lines."""

    file_path: str
    source: str  # "ai" | "human" | "mixed"
    confidence: float  # 0.0-1.0
    method: ProvenanceSource
    timestamp: datetime
    lines_range: tuple[int, int] | None = None
    model: str | None = None
    agent_tool: str | None = None
    session_id: str | None = None
    spec_ref: str | None = None
    cost_usd: float | None = None
    signature: str | None = None


@dataclass
class ConfigChange:
    """A detected change in an agent configuration file."""

    file_path: str
    field_path: str
    old_value: str | None
    new_value: str | None
    severity: ChangeSeverity
    description: str
    timestamp: datetime
    commit_sha: str | None = None


@dataclass
class ControlRequirement:
    """A single compliance requirement from a framework."""

    id: str
    framework: str
    name: str
    description: str
    article_ref: str | None = None
    category: str | None = None


@dataclass
class ControlResult:
    """Result of evaluating a single compliance control."""

    requirement: ControlRequirement
    status: ComplianceStatus
    evidence: str
    details: str = ""
    source: str = "auto"
    recommendations: list[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ComplianceSummary:
    """Summary statistics for a compliance evaluation."""

    framework: str
    total_controls: int
    compliant: int
    partial: int
    non_compliant: int
    not_applicable: int
    not_evaluated: int
    compliance_rate: float
    evaluated_at: datetime = field(default_factory=datetime.now)


@dataclass
class GapItem:
    """A compliance gap with actionable recommendation."""

    requirement: ControlRequirement
    status: ComplianceStatus
    gap_description: str
    recommendation: str
    effort: str  # "low", "medium", "high"
    tools_suggested: list[str] = field(default_factory=list)
    priority: int = 0
