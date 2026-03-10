# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Phase 1 — Foundation

- **Project structure** — Complete project scaffolding with `pyproject.toml`, editable install via hatchling, and full directory layout for all V0 modules.
- **Configuration system** (`src/licit/config/`)
  - Pydantic v2 schema with 9 config models covering provenance, changelog, frameworks, connectors, FRIA, Annex IV, and report settings.
  - YAML config loader with 3-level resolution: explicit path → `.licit.yaml` in cwd → defaults.
  - `save_config()` for persisting configuration changes.
- **Core data models** (`src/licit/core/models.py`)
  - 3 enums: `ComplianceStatus`, `ChangeSeverity`, `ProvenanceSource` (using `StrEnum`).
  - 6 dataclasses: `ProvenanceRecord`, `ConfigChange`, `ControlRequirement`, `ControlResult`, `ComplianceSummary`, `GapItem`.
- **Project auto-detection** (`src/licit/core/project.py`)
  - `ProjectDetector` with 8 detection methods: name, languages (Python/JS/TS/Go/Rust/Java), frameworks (FastAPI/Flask/Django/React/Next/Express), agent configs (10 patterns), CI/CD (GitHub Actions/GitLab CI/Jenkins/CircleCI), testing, security tools, git info.
  - `ProjectContext` dataclass with 20+ fields across 6 categories.
- **Evidence collection** (`src/licit/core/evidence.py`)
  - `EvidenceBundle` with 18 fields covering provenance, changelog, FRIA, guardrails, audit trail, human oversight, and security findings.
  - `EvidenceCollector` gathers evidence from `.licit/` data, project configs (architect guardrails, quality gates, budget), CI/CD, architect reports, and SARIF files.
- **CLI with 10 commands** (`src/licit/cli.py`)
  - `licit init` — Initialize project with auto-detection and `.licit.yaml` creation.
  - `licit trace` — Track code provenance (skeleton, Phase 2).
  - `licit changelog` — Agent config changelog (skeleton, Phase 3).
  - `licit fria` — FRIA questionnaire (skeleton, Phase 4).
  - `licit annex-iv` — Annex IV documentation (skeleton, Phase 4).
  - `licit report` — Unified compliance report (skeleton, Phase 6).
  - `licit gaps` — Gap analysis (skeleton, Phase 6).
  - `licit verify` — CI/CD gate with exit codes 0/1/2 (skeleton, Phase 4-6).
  - `licit status` — Show project compliance status.
  - `licit connect` — Enable/disable optional connectors.
- **Logging** (`src/licit/logging/setup.py`) — structlog configuration with WARNING default level, verbose mode support.
- **Test suite** — 52 tests across 5 test files covering config schema, config loading, project detection, evidence collection, and all CLI commands.
- **Type safety** — Full mypy strict mode compliance across all 21 source files.
- **Code quality** — ruff linting with zero errors.

## [0.1.0] — Unreleased

Initial release target. V0 MVP with full compliance evaluation capabilities.
