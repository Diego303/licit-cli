"""Tests for configuration schema models."""

from licit.config.schema import (
    ChangelogConfig,
    ConnectorsConfig,
    FrameworkConfig,
    LicitConfig,
    ProvenanceConfig,
    ReportConfig,
)


class TestLicitConfig:
    """Tests for root configuration model."""

    def test_default_config_has_all_sections(self) -> None:
        config = LicitConfig()
        assert isinstance(config.provenance, ProvenanceConfig)
        assert isinstance(config.changelog, ChangelogConfig)
        assert isinstance(config.frameworks, FrameworkConfig)
        assert isinstance(config.connectors, ConnectorsConfig)
        assert isinstance(config.reports, ReportConfig)

    def test_default_frameworks_enabled(self) -> None:
        config = LicitConfig()
        assert config.frameworks.eu_ai_act is True
        assert config.frameworks.owasp_agentic is True
        assert config.frameworks.nist_ai_rmf is False
        assert config.frameworks.iso_42001 is False

    def test_default_provenance_config(self) -> None:
        config = LicitConfig()
        assert config.provenance.enabled is True
        assert config.provenance.methods == ["git-infer"]
        assert config.provenance.confidence_threshold == 0.6
        assert config.provenance.sign is False
        assert config.provenance.store_path == ".licit/provenance.jsonl"

    def test_default_connectors_disabled(self) -> None:
        config = LicitConfig()
        assert config.connectors.architect.enabled is False
        assert config.connectors.vigil.enabled is False

    def test_model_dump_roundtrip(self) -> None:
        config = LicitConfig()
        data = config.model_dump()
        restored = LicitConfig.model_validate(data)
        assert restored.provenance.methods == config.provenance.methods
        assert restored.frameworks.eu_ai_act == config.frameworks.eu_ai_act

    def test_partial_config_fills_defaults(self) -> None:
        data = {"frameworks": {"eu_ai_act": True, "owasp_agentic": False}}
        config = LicitConfig.model_validate(data)
        assert config.frameworks.eu_ai_act is True
        assert config.frameworks.owasp_agentic is False
        # Other fields should have defaults
        assert config.provenance.enabled is True
        assert config.reports.default_format == "markdown"

    def test_changelog_default_watch_files(self) -> None:
        config = LicitConfig()
        assert "CLAUDE.md" in config.changelog.watch_files
        assert ".cursorrules" in config.changelog.watch_files
        assert "AGENTS.md" in config.changelog.watch_files
