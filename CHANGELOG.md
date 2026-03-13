# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [0.3.0] — 2026-03-13

### Added

#### Phase 3 — Changelog

- **Config watcher** (`src/licit/changelog/watcher.py`)
  - `ConfigWatcher` monitors agent config files (CLAUDE.md, .cursorrules, etc.) across git history.
  - `ConfigSnapshot` dataclass with path, content, commit_sha, timestamp, author.
  - Uses `git log --format=%H\x01%aI\x01%an --follow` for robust history retrieval, newest-first.
  - Glob pattern support for watch_files (e.g., `.prompts/**/*.md`).
  - Size guard: `_MAX_CONTENT_BYTES = 1_048_576` on `git show` output to prevent memory exhaustion from accidentally tracked binary files.
  - All subprocess calls have explicit timeouts (10s for checks, 30s for log) and `check=False`.
- **Semantic differ** (`src/licit/changelog/differ.py`)
  - Format-aware diffing dispatched by file extension: YAML, JSON, Markdown, plain text.
  - `FieldDiff` dataclass with `field_path`, `old_value`, `new_value`, `is_addition`, `is_removal`.
  - YAML/JSON: recursive dict diff with `_coerce_to_dict()` that wraps non-dict roots as `{"(root)": data}` instead of silently dropping data.
  - Markdown: section-aware diff using `_parse_md_sections()` with fenced code block tracking (prevents false heading detection inside ``` blocks).
  - Plain text: whole-file diff with added/removed line counts.
- **Change classifier** (`src/licit/changelog/classifier.py`)
  - Segment-based field matching via `_field_matches()` — `llm.model` matches pattern `model` but `model_config` does NOT (prevents false MAJOR classifications).
  - `_MAJOR_FIELDS` frozenset: model, llm.model, agent.model, provider, backend, llm.provider.
  - `_MINOR_FIELDS` frozenset: system_prompt, prompt, instructions, guardrails, rules, quality_gates, tools, allowed_tools, blocked_commands, protected_files.
  - Removal escalation: removing a MINOR-level field escalates to MAJOR severity.
  - Markdown section changes default to MINOR; everything else is PATCH.
  - Timezone-safe: uses `datetime.now(tz=UTC)` as fallback timestamp.
- **Changelog renderer** (`src/licit/changelog/renderer.py`)
  - Markdown output: grouped by file, sorted by severity (MAJOR first) then timestamp descending, with summary counts and per-file sections.
  - JSON output: structured records with `ensure_ascii=False` for unicode support.
  - Timezone-aware sorting (no naive/aware mixing).
- **CLI integration** — `licit changelog` now fully functional:
  - Real imports replacing `# type: ignore[import-not-found]` stubs.
  - Pipeline: watcher → differ → classifier → renderer.
  - `--format json` flag for JSON output.
  - `--since` flag for time-scoped analysis.
  - File write with `try/except OSError` error handling; output echoed before save attempt.
- **Test fixtures** — 5 fixture files for reproducible testing:
  - `claude_md_v1.md` / `claude_md_v2.md` — CLAUDE.md version pairs with section changes.
  - `cursorrules_v1.txt` — TypeScript rules for plain text diffing.
  - `architect_config_v1.yaml` / `architect_config_v2.yaml` — YAML configs with model and guardrail changes.

#### QA Hardening — Phase 3

- **Bug fixes** — 7 issues found and fixed during QA review:
  - **(High)** `classifier.py`: Substring matching (`"model" in field`) caused false MAJOR on `model_config`, `system_model` — replaced with segment-based `_field_matches()`.
  - **(High)** `differ.py`: Non-dict YAML/JSON roots (e.g., list `[item1, item2]`) silently dropped as `{}` — replaced with `_coerce_to_dict()` wrapping as `{"(root)": data}`.
  - **(High)** `watcher.py`: `git show` without size limit could load GBs of binary content — added `_MAX_CONTENT_BYTES = 1_048_576` guard.
  - **(High)** `classifier.py` + `renderer.py`: `datetime.now()` without timezone (DTZ005) created naive timestamps; mixing with git's timezone-aware timestamps in renderer sort could cause `TypeError` — fixed to `datetime.now(tz=UTC)`.
  - **(Medium)** `cli.py`: `Path.write_text()` could fail with `OSError` on read-only dirs — wrapped in `try/except`, moved `click.echo()` before write.
  - **(Medium)** `watcher.py`: `_file_has_git_history()` didn't log on timeout or failure — added `logger.debug` for both paths.
  - **(Low)** `differ.py`: Markdown headings inside fenced code blocks (```) were parsed as real sections — added `in_code_block` tracking in `_parse_md_sections()`.
- **93 new changelog tests** across 6 test files:
  - `test_watcher.py` (12) — git history, globs, edge cases, deleted files, deduplication.
  - `test_differ.py` (19) — YAML/JSON/MD/text diffs, non-dict roots, code blocks, empty content.
  - `test_classifier.py` (22) — field matching, severities, escalation, truncation, segment matching.
  - `test_renderer.py` (10) — Markdown/JSON rendering, grouping, sorting, empty changes.
  - `test_integration.py` (3) — full pipeline markdown, JSON, and empty case.
  - `test_qa_edge_cases.py` (27) — CLI commands (no-git, real-git, JSON format), unicode handling, timezone mixing, differ/classifier/renderer edge cases, import safety.

### Changed

- Test suite expanded from 280 to 373 tests (280 previous + 93 Phase 3).
- `licit changelog` command now fully functional (was skeleton in Phase 1).
- CLI imports for changelog modules changed from lazy `type: ignore` stubs to real imports.
- `pyproject.toml` version bumped to `0.3.0`.

## [0.2.0] — 2026-03-11

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
- **Documentation** (`docs/`) — 10 documents in Spanish: architecture, CLI guide, configuration guide, data models, security, compliance, best practices, development guide, FAQ, and quick start.

#### QA Hardening — Phase 1

- **Bug fixes** — 6 issues found and fixed during QA review:
  - `confidence_threshold` now validated to [0.0, 1.0] range (was accepting any float).
  - `_detect_git` exception handling broadened from `FileNotFoundError` to `OSError` (catches `PermissionError`).
  - `_parse_architect_config` narrowed from `except Exception` to specific exception types.
  - `has_dry_run`/`has_rollback` now conditional on architect config data (was unconditionally `True`).
  - Project name detection now prioritizes `pyproject.toml` over `package.json` when both exist.
  - Changelog entry count now only counts `## ` headers, ignoring `###` and deeper.
- **61 new QA tests** (`tests/test_qa_edge_cases.py`) covering:
  - Config validation: threshold bounds, unicode, empty YAML, extra fields, null values.
  - Core models: all enum memberships, dataclass instantiation, defaults, serialization.
  - ProjectDetector: Rust/Java detection, malformed configs, dual config files, all security tools.
  - EvidenceCollector: missing modules, malformed YAML/SARIF, non-vigil SARIF filtering, header counting.
  - CLI integration: connect persists to disk, init→status flow, invalid choices, verbose flag.
  - Import safety: no circular imports across all modules.

#### Phase 2 — Provenance

- **Heuristic scoring engine** (`src/licit/provenance/heuristics.py`)
  - 6 weighted heuristics for AI commit detection: author patterns, message patterns, bulk changes, co-author trailers, file patterns, time patterns.
  - Weighted average of only signaling heuristics (non-zero score), preventing silent heuristics from diluting strong signals.
  - Custom pattern loading from JSON file with invalid regex protection.
- **Git history analyzer** (`src/licit/provenance/git_analyzer.py`)
  - Parses `git log` output with `\x00`/`\x01` separators for robust parsing (handles pipes, quotes, special chars in commit messages).
  - `CommitInfo` dataclass with 9 fields; numstat parsing with `split("\t", 2)` for tab-in-filename safety.
  - Agent inference from 8 keyword patterns (claude→claude-code, cursor→cursor, copilot, codex, devin, architect).
  - Model inference from 8 regex patterns (claude-opus-4, claude-sonnet-4, gpt-4.1, gpt-4o, o1, gemini, deepseek).
  - Classification thresholds: >=0.7 → "ai", >=0.5 → "mixed", <0.5 → "human".
  - 30-second subprocess timeout; case-insensitive co-author extraction.
- **Append-only JSONL store** (`src/licit/provenance/store.py`)
  - `ProvenanceStore` with `append()`, `load_all()`, `get_stats()`, `get_by_file()`.
  - Datetime ISO serialization, lines_range tuple↔list conversion, corrupt line skip with logging.
  - Stats with deduplication (latest timestamp per file wins) and ai_percentage calculation.
- **Cryptographic attestation** (`src/licit/provenance/attestation.py`)
  - HMAC-SHA256 record signing and timing-safe verification via `hmac.compare_digest`.
  - Merkle tree batch signing (SHA256 leaves → binary tree → root hash).
  - Key management: explicit path → `.licit/.signing-key` → auto-generate with `os.urandom(32)`.
  - All filesystem access wrapped in `try/except OSError`.
- **Session reader framework** (`src/licit/provenance/session_readers/`)
  - `SessionReader` Protocol (not ABC) for extensible agent log parsing.
  - `ClaudeCodeSessionReader` — reads JSONL session files from `~/.claude/projects/` or configured directories.
  - Extracts provenance from `Write`/`Edit` tool_use entries; handles null params, non-string fields, invalid timestamps.
- **Provenance report generator** (`src/licit/provenance/report.py`)
  - Markdown report with summary table, AI tools, models, and file details sections.
  - Deduplication (latest record per file), pipe character escaping in file paths, auto-creates parent directories.
- **Provenance tracker** (`src/licit/provenance/tracker.py`)
  - Orchestrates git analysis + session reading + confidence filtering + attestation + store.
  - Respects `ProvenanceConfig`: enabled flag, methods list, confidence_threshold, sign flag.
  - Human records always pass threshold filter (by design).
- **CLI integration** — `licit trace` now uses real provenance implementations (no more lazy imports with `type: ignore`).
- **Evidence integration** — `EvidenceCollector` directly imports `ProvenanceStore` for real provenance stats.
- **Test fixtures** — Git log samples and Claude Code session samples for reproducible testing.

#### QA Hardening — Phase 2

- **Bug fixes** — 9 issues found and fixed during QA review:
  - **(Critical)** `git_analyzer.py`: embedded null byte in subprocess argument prevented all real execution — fixed with git hex escapes `%x00`/`%x01`.
  - **(High)** `heuristics.py`: `re.search()` crashed on invalid custom regex patterns — wrapped in `try/except re.error`.
  - **(High)** `claude_code.py`: `params: null` in JSON caused crash — added `isinstance` check before dict access.
  - **(High)** `evidence.py`: `len(None)` when guardrail YAML values explicitly null — changed to `or []` pattern.
  - **(Low)** `git_analyzer.py`: `split("\t")` without limit could break filenames with tabs — fixed with `split("\t", 2)`.
  - **(Low)** `git_analyzer.py`: Co-author regex was not case-insensitive — added `re.IGNORECASE`.
  - **(Low)** `claude_code.py`: Invalid timestamps fell silently to `now()` — added `logger.warning`.
  - **(Low)** `attestation.py`: Key file read/write lacked OSError handling — added `try/except OSError`.
  - **(Low)** `report.py`: Pipe characters in file paths broke markdown table — added `replace("|", "\\|")`.
- **81 new QA tests** (`tests/test_provenance/test_qa_edge_cases.py`) covering:
  - Regression tests for all 3 high-severity bugs.
  - Heuristics: unicode, score cap, all-heuristics-fire, hour boundaries, invalid patterns.
  - Git analyzer: unicode paths/authors, tab filenames, malformed dates, timeout, empty commits.
  - Store: unicode roundtrip, 500 records, blank lines, deep dirs, signature preservation.
  - Attestation: empty/nested/unicode data, different keys, odd Merkle, non-writable dirs.
  - Session reader: null/list/string params, non-string tools, multiple dirs, bash redirect.
  - Report: empty/single/dedup, pipe escape, unicode, sorted files, parent dirs.
  - Cross-module: git→store→report pipeline, sign+store+verify, session→store roundtrip.
  - Tracker: empty methods, unknown method, threshold=0.
- **E2E integration test** — Full pipeline tested on real git repo: analyze → store → report → sign → verify.

### Changed

- Test suite expanded from 52 to 280 tests (52 original + 61 Phase 1 QA + 86 Phase 2 + 81 Phase 2 QA).
- `licit trace` command now fully functional (was skeleton in Phase 1).
- `EvidenceCollector` uses real `ProvenanceStore` import (removed `try/except ImportError` fallback).

## [0.1.0] — 2026-03-10

Initial release. Foundation: config system, project auto-detection, evidence collection, CLI skeleton (10 commands, 3 functional), 113 tests.
