"""Tests for configuration loading."""

from pathlib import Path

import yaml

from licit.config.loader import load_config, save_config
from licit.config.schema import LicitConfig


class TestLoadConfig:
    """Tests for config file loading."""

    def test_load_returns_defaults_when_no_file(self, tmp_path: Path) -> None:
        import os

        original = os.getcwd()
        try:
            os.chdir(tmp_path)
            config = load_config(None)
            assert config.frameworks.eu_ai_act is True
            assert config.provenance.enabled is True
        finally:
            os.chdir(original)

    def test_load_from_explicit_path(self, tmp_path: Path) -> None:
        config_file = tmp_path / "custom.yaml"
        config_file.write_text(
            yaml.dump({
                "frameworks": {"eu_ai_act": True, "owasp_agentic": False},
                "provenance": {"confidence_threshold": 0.8},
            }),
            encoding="utf-8",
        )
        config = load_config(str(config_file))
        assert config.frameworks.owasp_agentic is False
        assert config.provenance.confidence_threshold == 0.8

    def test_load_from_cwd_default(self, tmp_path: Path) -> None:
        import os

        config_file = tmp_path / ".licit.yaml"
        config_file.write_text(
            yaml.dump({"frameworks": {"eu_ai_act": False}}),
            encoding="utf-8",
        )
        original = os.getcwd()
        try:
            os.chdir(tmp_path)
            config = load_config(None)
            assert config.frameworks.eu_ai_act is False
        finally:
            os.chdir(original)

    def test_load_invalid_yaml_returns_defaults(self, tmp_path: Path) -> None:
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("{{invalid yaml", encoding="utf-8")
        config = load_config(str(config_file))
        # Should fall back to defaults
        assert config.frameworks.eu_ai_act is True

    def test_load_nonexistent_path_returns_defaults(self) -> None:
        config = load_config("/nonexistent/path/config.yaml")
        assert config.frameworks.eu_ai_act is True

    def test_load_non_dict_yaml_returns_defaults(self, tmp_path: Path) -> None:
        config_file = tmp_path / "list.yaml"
        config_file.write_text("- item1\n- item2\n", encoding="utf-8")
        config = load_config(str(config_file))
        assert config.frameworks.eu_ai_act is True


class TestSaveConfig:
    """Tests for saving configuration."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        config = LicitConfig()
        path = save_config(config, str(tmp_path / ".licit.yaml"))
        assert path.exists()

    def test_save_roundtrip(self, tmp_path: Path) -> None:
        config = LicitConfig()
        config.frameworks.owasp_agentic = False
        config.provenance.confidence_threshold = 0.9

        path = save_config(config, str(tmp_path / ".licit.yaml"))
        loaded = load_config(str(path))
        assert loaded.frameworks.owasp_agentic is False
        assert loaded.provenance.confidence_threshold == 0.9

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        config = LicitConfig()
        path = save_config(config, str(tmp_path / "deep" / "nested" / ".licit.yaml"))
        assert path.exists()
