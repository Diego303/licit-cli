"""Shared test fixtures for licit."""

import logging
from pathlib import Path

import pytest
import structlog

from licit.core.evidence import EvidenceBundle
from licit.core.project import (
    AgentConfigFile,
    CICDConfig,
    ProjectContext,
    SecurityTooling,
)

# Configure structlog for tests — suppress all output
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL),
    context_class=dict,
    logger_factory=structlog.WriteLoggerFactory(),
    cache_logger_on_first_use=False,
)


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project directory for testing."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test-project"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    return tmp_path


@pytest.fixture
def git_project(tmp_path: Path) -> Path:
    """Create a temporary directory with git initialized."""
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    # Create initial commit
    (tmp_path / "README.md").write_text("# Test\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    return tmp_path


def make_context(
    root_dir: str = "/tmp/test",
    name: str = "test-project",
    languages: list[str] | None = None,
    agent_configs: list[AgentConfigFile] | None = None,
    has_architect: bool = False,
    architect_config_path: str | None = None,
    cicd_platform: str = "none",
    git_initialized: bool = True,
    total_commits: int = 50,
    security: SecurityTooling | None = None,
) -> ProjectContext:
    """Build a ProjectContext for testing."""
    return ProjectContext(
        root_dir=root_dir,
        name=name,
        languages=languages or ["python"],
        agent_configs=agent_configs or [],
        has_architect=has_architect,
        architect_config_path=architect_config_path,
        cicd=CICDConfig(platform=cicd_platform),
        git_initialized=git_initialized,
        total_commits=total_commits,
        security=security or SecurityTooling(),
    )


def make_evidence(
    has_provenance: bool = False,
    provenance_stats: dict[str, object] | None = None,
    has_fria: bool = False,
    fria_path: str | None = None,
    has_annex_iv: bool = False,
    annex_iv_path: str | None = None,
    has_guardrails: bool = False,
    guardrail_count: int = 0,
    has_quality_gates: bool = False,
    quality_gate_count: int = 0,
    has_budget_limits: bool = False,
    has_audit_trail: bool = False,
    audit_entry_count: int = 0,
    has_human_review_gate: bool = False,
    has_changelog: bool = False,
    changelog_entry_count: int = 0,
    has_dry_run: bool = False,
    has_rollback: bool = False,
) -> EvidenceBundle:
    """Build an EvidenceBundle for testing."""
    return EvidenceBundle(
        has_provenance=has_provenance,
        provenance_stats=provenance_stats or {},
        has_fria=has_fria,
        fria_path=fria_path,
        has_annex_iv=has_annex_iv,
        annex_iv_path=annex_iv_path,
        has_guardrails=has_guardrails,
        guardrail_count=guardrail_count,
        has_quality_gates=has_quality_gates,
        quality_gate_count=quality_gate_count,
        has_budget_limits=has_budget_limits,
        has_audit_trail=has_audit_trail,
        audit_entry_count=audit_entry_count,
        has_human_review_gate=has_human_review_gate,
        has_changelog=has_changelog,
        changelog_entry_count=changelog_entry_count,
        has_dry_run=has_dry_run,
        has_rollback=has_rollback,
    )
