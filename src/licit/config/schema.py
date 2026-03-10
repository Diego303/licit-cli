"""Pydantic v2 configuration schema for licit."""

from pydantic import BaseModel, Field


class ProvenanceConfig(BaseModel):
    """Provenance tracking configuration."""

    enabled: bool = True
    methods: list[str] = Field(
        default_factory=lambda: ["git-infer"],
        description="Methods: git-infer, session-log, git-ai",
    )
    session_dirs: list[str] = Field(
        default_factory=list,
        description="Directories with agent session logs",
    )
    sign: bool = False
    sign_key_path: str | None = None
    confidence_threshold: float = Field(
        default=0.6,
        description="Minimum confidence to count as AI-generated",
    )
    store_path: str = ".licit/provenance.jsonl"


class ChangelogConfig(BaseModel):
    """Changelog configuration."""

    enabled: bool = True
    watch_files: list[str] = Field(
        default_factory=lambda: [
            "CLAUDE.md",
            ".cursorrules",
            ".cursor/rules",
            "AGENTS.md",
            ".github/copilot-instructions.md",
            ".github/agents/*.md",
            ".architect/config.yaml",
            "architect.yaml",
        ],
    )
    output_path: str = ".licit/changelog.md"


class FrameworkConfig(BaseModel):
    """Regulatory framework configuration."""

    eu_ai_act: bool = True
    owasp_agentic: bool = True
    nist_ai_rmf: bool = False
    iso_42001: bool = False


class ConnectorArchitectConfig(BaseModel):
    """Architect connector configuration."""

    enabled: bool = False
    reports_dir: str = ".architect/reports"
    audit_log: str | None = None
    config_path: str | None = None


class ConnectorVigilConfig(BaseModel):
    """Vigil connector configuration."""

    enabled: bool = False
    sarif_path: str | None = None
    sbom_path: str | None = None


class ConnectorsConfig(BaseModel):
    """All connector configurations."""

    architect: ConnectorArchitectConfig = Field(default_factory=ConnectorArchitectConfig)
    vigil: ConnectorVigilConfig = Field(default_factory=ConnectorVigilConfig)


class FRIAConfig(BaseModel):
    """FRIA document configuration."""

    output_path: str = ".licit/fria-report.md"
    data_path: str = ".licit/fria-data.json"
    organization: str = ""
    system_name: str = ""
    system_description: str = ""


class AnnexIVConfig(BaseModel):
    """Annex IV documentation configuration."""

    output_path: str = ".licit/annex-iv.md"
    organization: str = ""
    product_name: str = ""
    product_version: str = ""


class ReportConfig(BaseModel):
    """Report output configuration."""

    output_dir: str = ".licit/reports"
    default_format: str = "markdown"
    include_evidence: bool = True
    include_recommendations: bool = True


class LicitConfig(BaseModel):
    """Root configuration for licit."""

    provenance: ProvenanceConfig = Field(default_factory=ProvenanceConfig)
    changelog: ChangelogConfig = Field(default_factory=ChangelogConfig)
    frameworks: FrameworkConfig = Field(default_factory=FrameworkConfig)
    connectors: ConnectorsConfig = Field(default_factory=ConnectorsConfig)
    fria: FRIAConfig = Field(default_factory=FRIAConfig)
    annex_iv: AnnexIVConfig = Field(default_factory=AnnexIVConfig)
    reports: ReportConfig = Field(default_factory=ReportConfig)
