"""Load and merge configuration from YAML file, defaults, and CLI overrides."""

from pathlib import Path

import click
import structlog
import yaml

from licit.config.defaults import CONFIG_FILENAME
from licit.config.schema import LicitConfig

logger = structlog.get_logger()


def load_config(config_path: str | None = None) -> LicitConfig:
    """Load configuration from YAML file, falling back to defaults.

    Resolution order:
    1. Explicit path (--config flag)
    2. .licit.yaml in current directory
    3. Default values from schema
    """
    path = _resolve_config_path(config_path)

    if path is not None:
        return _load_from_file(path)

    logger.debug("config_not_found", msg="Using default configuration")
    return LicitConfig()


def _resolve_config_path(explicit_path: str | None) -> Path | None:
    """Find the config file to load."""
    if explicit_path:
        p = Path(explicit_path)
        if p.exists():
            return p
        logger.warning("config_path_not_found", path=explicit_path)
        return None

    default = Path.cwd() / CONFIG_FILENAME
    if default.exists():
        return default

    return None


def _load_from_file(path: Path) -> LicitConfig:
    """Parse YAML config file into LicitConfig."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        logger.error("config_parse_error", path=str(path), error=str(exc))
        click.echo(
            f"  Warning: {path} has invalid YAML — using defaults. "
            f"Run with --verbose for details.",
            err=True,
        )
        return LicitConfig()

    if not isinstance(raw, dict):
        logger.warning("config_not_dict", path=str(path))
        click.echo(
            f"  Warning: {path} does not contain a YAML mapping — using defaults.",
            err=True,
        )
        return LicitConfig()

    try:
        config = LicitConfig.model_validate(raw)
    except Exception as exc:
        logger.error("config_validation_error", path=str(path), error=str(exc))
        click.echo(
            f"  Warning: {path} has invalid values — using defaults. "
            f"Run with --verbose for details.",
            err=True,
        )
        return LicitConfig()

    logger.debug("config_loaded", path=str(path))
    return config


def save_config(config: LicitConfig, path: str | None = None) -> Path:
    """Save config to YAML file."""
    target = Path(path) if path else Path.cwd() / CONFIG_FILENAME
    target.parent.mkdir(parents=True, exist_ok=True)

    data = config.model_dump(exclude_defaults=False)
    target.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    logger.debug("config_saved", path=str(target))
    return target
