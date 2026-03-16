# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [1.0.0] — 2026-03-16

### Added

- **`licit fria --auto`** — Non-interactive mode for CI/CD pipelines. Accepts all auto-detected values and uses first-choice defaults for unanswered questions. Generates both `fria-data.json` and `fria-report.md` without requiring TTY input.

### Fixed

#### QA Hardening — V0 Exhaustive Test (142 tests, 5 projects, 10 edge cases)

Full QA sweep across 5 simulated projects (Python/FastAPI, Node/Express, Rust, empty repo, architect+vigil) with all command/flag combinations, edge cases, and cross-command coherence checks.

- **(Critical)** `git_analyzer.py`: `trace --since` did not filter commits by date. Root cause: git's `--since` flag filters by **committer date** (when the commit was physically made), not **author date** (the date recorded in `--date=` overrides). Commits created today with `--date=2026-01-10` would pass a `--since=2026-01-11` filter because their committer date was today. Fix: removed `--since` from git command, added `_filter_since()` method that filters parsed commits by author date in Python, with timezone-aware comparison (bare dates treated as UTC).
- **(Critical)** `store.py`: `licit trace` crashed with a full Python traceback (`PermissionError`) when `.licit/` directory had read-only permissions. Fix: `save()` method now catches `OSError` and raises `click.ClickException` with a clean user-facing message: `"Cannot write to .licit/provenance.jsonl: Permission denied. Check directory permissions."`.
- **(High)** `store.py`: Provenance store grew unboundedly — every `licit trace` run appended all records to the JSONL file. After 10 runs, a 37-record project had 370 lines. Fix: `save()` now merges incoming records with existing ones, deduplicating by file path (latest timestamp wins), then atomically rewrites the store. Store size is now proportional to unique files, not number of runs.
- **(High)** `cli.py`: `trace` displayed "Analyzed 37 file records" while `--stats` showed "Total files tracked: 35" — different numbers for the same data. Root cause: `trace` counted raw records (including duplicates from files touched in multiple commits) while `stats` counted unique files. Fix: `trace` now deduplicates for display, showing "Analyzed N files across M records".
- **(Medium)** `cli.py`: `changelog --format json` saved JSON content to `.licit/changelog.md` (a `.md` file), overwriting the Markdown version. Fix: output path extension now matches format — `--format json` saves to `.licit/changelog.json`.
- **(Medium)** `cli.py`: `reports.output_dir` configuration in `.licit.yaml` was ignored — reports always saved to hardcoded `.licit/reports/`. Fix: report command now reads `config.reports.output_dir` for the default output path.
- **(Medium)** `cli.py`: `licit init` silently overwrote existing `.licit.yaml` and `.licit/` directory on re-initialization. Fix: now displays "Warning: existing configuration found — overwriting." when config or data directory already exists.
- **(Medium)** `cli.py`: `licit gaps` displayed "No compliance gaps found! All requirements met." when no frameworks were enabled — misleading since nothing was evaluated. Same issue in `licit report` (showed "0/0 controls compliant"). Fix: both commands now check for empty framework list first and display "No frameworks enabled. Enable at least one framework in .licit.yaml."
- **(Low)** `loader.py`: Config parse errors (corrupt YAML, invalid values) were only logged via structlog — invisible to users not running with `--verbose`. Fix: `_load_from_file()` now emits a visible `click.echo` warning to stderr: "Warning: .licit.yaml has invalid YAML — using defaults. Run with --verbose for details."

### Changed

- **Provenance store architecture**: Changed from append-only to merge-and-replace. `ProvenanceStore.save()` (aliased as `append()` for backwards compatibility) now reads existing records, merges with new ones by file path (latest wins), and rewrites the store atomically. `get_stats()` no longer needs to deduplicate on read.
- **Since filtering architecture**: Date filtering for `trace --since` moved from git-level (`--since=` flag) to application-level (`_filter_since()` in `GitAnalyzer`). This correctly handles commits with overridden author dates, cherry-picks, and rebases.
- Test suite: 789 tests, all passing. Lint: 0 ruff errors.
- `pyproject.toml` version bumped to `1.0.0`.

## [0.7.0] — 2026-03-15

### Added

#### Phase 7 — Connectors + Integration

- **Connector protocol** (`src/licit/connectors/base.py`)
  - `Connector` Protocol (`@runtime_checkable`) defining `name`, `enabled`, `available()`, `collect(evidence)` interface.
  - `ConnectorResult` dataclass with computed `success` property (`files_read > 0 and no errors`) and `has_errors` property.
  - `EvidenceBundle` imported under `TYPE_CHECKING` only to prevent circular imports.
- **Architect connector** (`src/licit/connectors/architect.py`)
  - `ArchitectConnector` reads 3 data sources: JSON reports (`_read_reports`), audit JSONL logs (`_read_audit_log`), and config YAML (`_read_config`).
  - `ArchitectReport` and `AuditEntry` dataclasses with defensive `isinstance` checks on all JSON fields.
  - Config parsing extracts guardrails, quality gates, budget limits, dry-run/rollback capabilities.
  - `guardrail_count` uses `+=` (additive) so multiple sources can contribute.
  - `available()` checks for reports directory or config file on disk.
  - Malformed lines in audit JSONL are logged as errors but don't abort the read.
- **Vigil connector** (`src/licit/connectors/vigil.py`)
  - `VigilConnector` reads SARIF 2.1.0 files and CycloneDX SBOM.
  - `_resolve_sarif_paths()` supports explicit file, explicit directory (globs `*.sarif`), and auto-detected files from `ProjectContext.security.sarif_files`, with deduplication.
  - SARIF parsing refactored into 4 focused methods: `_parse_run`, `_extract_tool_name`, `_parse_finding`, `_extract_location` — each under C901/10 complexity.
  - Counts findings by severity: `error` → critical, `warning` → high, `note` → medium, other → low.
  - Parses all SARIF runs regardless of tool name (not limited to vigil-named tools).
  - SBOM reading validates JSON structure and counts as a file read (V0 scope; V1 will feed into OWASP ASI03).
  - SARIF severity constants: `SARIF_LEVEL_CRITICAL`, `SARIF_LEVEL_HIGH`, `SARIF_LEVEL_MEDIUM`, `SARIF_LEVEL_LOW`.
- **EvidenceCollector refactored** (`src/licit/core/evidence.py`)
  - `EvidenceCollector.__init__` now accepts optional `config: LicitConfig` parameter (backwards compatible).
  - When config is provided and connector is enabled, delegates to formal connector classes.
  - When config is absent or connector is disabled, falls back to inline detection that delegates to temporary connector instances — zero code duplication between paths.
  - `connector_results` property exposes `ConnectorResult` list from last `collect()` call.
  - Removed direct `json` and `yaml` imports (no longer needed).
- **CLI enhancements** (`src/licit/cli.py`)
  - All `EvidenceCollector` calls now pass `config` for connector support.
  - `licit connect architect`: auto-detects `config_path` if not set, shows data availability via `available()`.
  - `licit connect vigil`: detects SARIF files from project context, shows availability.
  - `licit status`: shows connector as "enabled" vs "detected", displays security findings count when > 0.
- **Config example** (`.licit.example.yaml`)
  - Full documented configuration with all fields including `connectors.architect.audit_log`, `connectors.vigil.sarif_path`, `connectors.vigil.sbom_path`.
- **Integration tests** (`tests/test_integration/test_full_flow.py`)
  - 10 end-to-end tests on a synthetic git project with AI commits, architect data, and vigil SARIF.
  - `TestFullFlow`: init → trace → report → gaps → verify → status.
  - `TestConnectCommand`: enable/disable connectors.
  - `TestConnectorEnrichedReport`: architect enrichment, changelog.
  - Uses `monkeypatch.chdir` for proper working directory isolation.
- **Test fixtures** (`tests/test_connectors/fixtures/`)
  - `architect_report.json`, `architect_report_2.json` — sample architect task reports.
  - `architect_audit.jsonl` — 6-entry audit log with task lifecycle events.
  - `architect_config.yaml` — config with guardrails (7 rules), quality gates (3), budget ($50).
  - `vigil_report.sarif` — SARIF 2.1.0 with 3 findings (1 error, 1 warning, 1 note).
  - `sbom.json` — CycloneDX SBOM with 3 components.

#### QA Hardening — Phase 7

- **Bug fixes** — 4 issues found and fixed during QA review:
  - **(High)** `vigil.py _parse_run()`: Cyclomatic complexity 18 (C901) — 18 nested branches for tool name extraction, finding parsing, and location extraction. Refactored into 3 focused static methods: `_extract_tool_name()`, `_parse_finding()`, `_extract_location()`.
  - **(Medium)** `vigil.py _read_sbom()`: `evidence` parameter unused (ARG002) — dead parameter removed from signature and call site.
  - **(Medium)** `architect.py _read_audit_log()`: `for line in ...: line = line.strip()` overwrote loop variable (PLW2901) — renamed to `raw_line`/`stripped`.
  - **(Medium)** `architect.py _read_config()`: `guardrail_count = X` used `=` instead of `+=` — second source would overwrite first. Changed to `+=` with regression test.
- **83 new Phase 7 tests** across 4 test files:
  - `test_architect.py` (22) — Protocol conformance (4), reports (4), audit log (4), config (6), availability (3), full collect (1).
  - `test_vigil.py` (22) — Protocol (3), SARIF reading (8), SARIF parsing (4), SBOM (3), availability (4).
  - `test_qa_edge_cases.py` (20) — Unicode in reports/SARIF (2), whitespace YAML (1), guardrail additive (1), 500-line audit log (1), minimal report (1), default config path (1), dry_run: false (1), 100 SARIF findings (1), unknown level (1), no tool section (1), empty dir (1), SBOM non-object (1), empty runs (1), ConnectorResult defaults (2), cross-module both connectors (1), null config paths (2), CLI invalid connector (1).
  - `test_evidence.py` (9 added) — Connector delegation (3), connector_results reset (1), ConnectorResult computed (4), non-vigil SARIF (1).
  - `test_full_flow.py` (10) — E2E init/trace/report/gaps/verify/status (6), connect enable/disable (2), enriched report/changelog (2).

### Changed

- Test suite expanded from 706 to 789 tests (706 previous + 83 Phase 7).
- `EvidenceCollector` now accepts optional `LicitConfig` parameter for formal connector support.
- Inline evidence collection paths (architect, vigil) now delegate to connector classes instead of duplicating parsing logic.
- `licit connect` command enhanced with data availability feedback.
- `licit status` command enhanced with connector enable state and security findings display.
- SARIF inline collector no longer filters by vigil tool name — all SARIF tools are counted (consistent with formal `VigilConnector`).
- `pyproject.toml` version bumped to `0.7.0`.

## [0.6.0] — 2026-03-15

### Added

#### Phase 6 — Reports + Gap Analyzer

- **Unified report generator** (`src/licit/reports/unified.py`)
  - `UnifiedReportGenerator` orchestrates multi-framework evaluation and produces a cross-framework report with aggregated statistics.
  - `UnifiedReport` and `FrameworkReport` dataclasses with `ComplianceSummary` per framework.
  - Exception-safe framework evaluation: a failing evaluator is skipped with `logger.exception()`, not propagated.
  - Respects `ReportConfig` flags: `include_evidence`, `include_recommendations`.
  - UTC timestamps via `datetime.now(tz=UTC)`.
- **Gap analyzer** (`src/licit/reports/gap_analyzer.py`)
  - `GapAnalyzer` identifies `NON_COMPLIANT` and `PARTIAL` results, converts them to `GapItem` instances with actionable recommendations.
  - `_TOOL_SUGGESTIONS` maps all 17 requirement categories (8 EU AI Act + 10 OWASP, `human-oversight` shared) to specific tool recommendations.
  - `_EFFORT_MAP` assigns effort estimates (`low`/`medium`/`high`) per category.
  - Gaps sorted by severity (non-compliant first), then assigned sequential priority.
  - Exception-safe: failing framework evaluators are skipped with logging.
- **Markdown reporter** (`src/licit/reports/markdown.py`)
  - Renders `UnifiedReport` as Markdown with overall summary table, per-framework sections, status icons (`[PASS]`/`[FAIL]`/`[PARTIAL]`), and conditional evidence/recommendations.
- **JSON reporter** (`src/licit/reports/json_fmt.py`)
  - Renders `UnifiedReport` as structured JSON with `ensure_ascii=False` for unicode support.
  - Conditional evidence/recommendations per `ReportConfig` flags.
- **HTML reporter** (`src/licit/reports/html.py`)
  - Renders `UnifiedReport` as a self-contained HTML file — no external CSS/JS dependencies.
  - Responsive CSS (max-width 960px), color-coded status badges, styled recommendation blocks.
  - XSS-safe `_esc()` function escaping 5 characters: `&`, `<`, `>`, `"`, `'`.
- **Terminal summary** (`src/licit/reports/summary.py`)
  - `print_summary()` prints a compact compliance overview with ASCII progress bars.
  - `_progress_bar()` renders `[####....]` with clamping to [0, width].
- **CLI integration** — `licit report`, `licit gaps`, `licit verify` now fully functional:
  - `licit report` supports `--format markdown|json|html` and `-o` custom output path.
  - `licit gaps` shows gaps with `[X]`/`[!]` icons, descriptions, recommendations, and tool suggestions.
  - `licit verify` returns exit code 0 (compliant), 1 (non-compliant), or 2 (partial).
  - All `# type: ignore[import-not-found]` stubs removed — real imports from `licit.reports.*`.
  - `_get_frameworks()` helper shared by all three commands.

#### QA Hardening — Phase 6

- **Bug fixes** — 7 issues found and fixed during QA review:
  - **(Critical)** `gap_analyzer.py`: 8 of 10 OWASP category keys did not match actual `owasp_agentic/requirements.py` categories. Used invented names (`excessive-agency`, `prompt-injection`, `sandboxing`, etc.) instead of actual ones (`access-control`, `input-security`, `isolation`, etc.). Result: all OWASP gaps had empty tool suggestions and default effort. Fixed by rewriting both `_TOOL_SUGGESTIONS` and `_EFFORT_MAP` with exact category keys from `requirements.py`.
  - **(High)** `unified.py` and `gap_analyzer.py`: No exception handling around `fw.evaluate()` calls — a crashing evaluator would take down the entire report or gap analysis. Fixed with `try/except Exception` + `logger.exception()`.
  - **(High)** No CLI integration tests for `report`, `gaps`, `verify` commands. Added 10 tests covering all formats, output paths, and exit codes.
  - **(Medium)** `html.py _esc()`: Did not escape single quotes (`'`), creating potential XSS risk if future attributes use single-quote delimiters. Added `.replace("'", "&#39;")`.
  - **(Medium)** `_TOOL_SUGGESTIONS["data-governance"]` was empty — data governance gaps showed no tool suggestions. Added `"licit annex-iv (document data practices)"`.
  - **(Low)** `markdown.py`, `json_fmt.py`, `html.py`: Imported `structlog` and created `logger` without using them. Removed dead imports.
  - **(Low)** `json_fmt.py`: `_framework_to_dict` parameter typed as `Any` instead of `FrameworkReport`. Fixed with `TYPE_CHECKING` import.
- **106 new Phase 6 tests** across 8 test files:
  - `test_unified.py` (12) — Empty/single/multi framework, totals, compliance rate, flags, exception handling (BrokenEvaluator).
  - `test_gap_analyzer.py` (15) — Empty/minimal/full gaps, sorting, priority, effort, descriptions, OWASP, multi-framework, exceptions, category completeness.
  - `test_markdown.py` (10) — Project name, sections, summary, icons, evidence, recommendations, footer, tables, empty.
  - `test_json_fmt.py` (10) — Valid JSON, project, overall, frameworks, fields, evidence, recommendations, counts, empty, timestamp.
  - `test_html.py` (12) — Valid HTML, project, sections, style, badges, HTML escaping (5 chars + single quotes), evidence, recommendations, footer, self-contained, empty.
  - `test_summary.py` (11) — Progress bar (0%/50%/100%/clamped/negative), prints (project, frameworks, overall, bar, empty).
  - `test_qa_edge_cases.py` (26) — Category mapping completeness (cross-references requirements.py), unicode handling (3 formats), boundary inputs (empty evidence, None category, unknown category, all-compliant), cross-module integration roundtrips (5), HTML escaping edge cases (4).
  - `test_cli.py` (10 added) — Report markdown/json/html, custom output, summary print, gaps with recommendations, verify exit codes.

### Changed

- Test suite expanded from 600 to 706 tests (600 previous + 106 Phase 6).
- `licit report`, `licit gaps`, `licit verify` now fully functional (were stubs with `# type: ignore`).
- CLI imports for reports modules changed from lazy `type: ignore` stubs to real imports.
- `pyproject.toml` version bumped to `0.6.0`.

## [0.5.0] — 2026-03-14

### Added

#### Phase 5 — OWASP Agentic Top 10 Framework

- **OWASP Agentic requirements** (`src/licit/frameworks/owasp_agentic/requirements.py`)
  - 10 `ControlRequirement` definitions covering all OWASP Agentic Top 10 risks (ASI01–ASI10).
  - 10 categories: access-control, input-security, supply-chain, observability, output-security, human-oversight, isolation, resource-limits, error-handling, data-protection.
  - Reference: OWASP Top 10 for Agentic AI Security (2025).
  - Helper functions: `get_requirement(id)` and `get_requirements_by_category(category)`.
- **OWASP Agentic evaluator** (`src/licit/frameworks/owasp_agentic/evaluator.py`)
  - `OWASPAgenticEvaluator` with dynamic method dispatch via `getattr(self, f"_eval_{id}")` — same pattern as EU AI Act evaluator.
  - Dedicated evaluation methods for all 10 risks with scoring logic:
    - ASI01: Excessive Agency (guardrails +1, quality gates +1, budget +1, agent configs +1; compliant at 3+).
    - ASI02: Prompt Injection (vigil +2, guardrails +1, human review +1; compliant at 3+).
    - ASI03: Supply Chain (SCA tools +2, changelog +1, versioned configs +1; compliant at 3+).
    - ASI04: Logging & Monitoring (git +1, audit trail +2, provenance +1, OTel +1; compliant at 3+).
    - ASI05: Output Handling (human review +2, quality gates +1, test suite +1; compliant at 3+).
    - ASI06: Human Oversight (human review +2, dry-run +1, quality gates +1, rollback +1; compliant at 3+).
    - ASI07: Sandboxing (guardrails +2, CI/CD +1, agent configs +1; compliant at 3+).
    - ASI08: Resource Consumption (budget limits +2, quality gates +1; compliant at 2+).
    - ASI09: Error Handling (test suite +1, CI/CD +1, rollback +1; compliant at 2+).
    - ASI10: Data Exposure (guardrails +1, security scanning +2, agent configs +1; compliant at 3+).
  - `_score_to_status()` helper with configurable thresholds (same as EU AI Act).
  - `_safe_float(value, *, field)` for defensive provenance stats access with contextual logging.
  - Smart evidence messages: `guardrail_count=0` shows "configured" instead of misleading "0 rules".
- **Jinja2 template** (`src/licit/frameworks/owasp_agentic/templates/report_section.md.j2`)
  - Report section template aligned with EU AI Act format for uniform Phase 6 consumption.
  - Summary table + per-requirement details with status, reference, evidence, recommendations.

#### QA Hardening — Phase 5

- **Bug fixes** — 3 issues found and fixed during QA review:
  - **(Medium)** `report_section.md.j2`: Template format inconsistent with EU AI Act (`####` vs `###` headings, `status.value` vs `status`, em dash vs parentheses) — aligned to match EU AI Act exactly.
  - **(Low)** `evaluator.py`: `_safe_float` hardcoded `field="ai_percentage"` in debug log despite generic function name — added `field` keyword parameter with default `"unknown"`.
  - **(Low)** `evaluator.py`: `has_guardrails=True` with `guardrail_count=0` produced "Guardrails limit agent scope: 0 rules" — added conditional branch showing "configured" instead.
- **103 new Phase 5 tests** across 3 test files:
  - `test_evaluator.py` (40) — Properties (4), full evaluation (5), ASI01-ASI10 compliance paths (31).
  - `test_requirements.py` (15) — Data integrity (9), get_requirement (3), get_by_category (3).
  - `test_qa_edge_cases.py` (48) — Protocol conformance (3), `_score_to_status` boundaries (8), `_safe_float` robustness (8), evaluator edge cases (17: provenance stats, OTel bonus, SCA tools, CI/CD display, idempotency, compliant→empty recs, non-compliant→has recs, security_findings neutrality, guardrail_count=0, template rendering), registry interop (3), CLI integration (3), requirements integrity (4), cross-module (3).
- **CLI integration** — `licit verify --framework owasp`, `licit report --framework owasp`, and `licit gaps --framework owasp` now fully functional:
  - Real import replacing `# type: ignore[import-not-found]` stub for `OWASPAgenticEvaluator`.
- **Test infrastructure** — `conftest.py` `make_evidence()` expanded with 5 new parameters:
  - `has_otel`, `has_requirements_traceability`, `security_findings_total`, `security_findings_critical`, `security_findings_high` — now covers 100% of `EvidenceBundle` fields.

### Changed

- Test suite expanded from 497 to 600 tests (497 previous + 103 Phase 5).
- `licit verify --framework owasp` now evaluates 10 OWASP risks and returns exit codes 0/1/2.
- `licit verify --framework all` now evaluates both EU AI Act (11 articles) and OWASP (10 risks).
- CLI import for OWASP module changed from lazy `type: ignore` stub to real import.
- `pyproject.toml` version bumped to `0.5.0`.

## [0.4.0] — 2026-03-14

### Added

#### Phase 4 — EU AI Act Framework

- **Framework protocol + registry** (`src/licit/frameworks/`)
  - `ComplianceFramework` Protocol (`base.py`) — `@runtime_checkable` structural typing with `name`, `version`, `description` properties, `get_requirements()`, and `evaluate()` methods.
  - `FrameworkRegistry` (`registry.py`) — Dict-based registry with `register()`, `get()`, `list_all()`, `names()`. Global singleton via `get_registry()`. Infrastructure for Phase 6 unified reports.
- **EU AI Act requirements** (`src/licit/frameworks/eu_ai_act/requirements.py`)
  - 11 `ControlRequirement` definitions covering Articles 9, 10, 12, 13, 14, 14(4)(a), 14(4)(d), 26, 26(5), 27, and Annex IV.
  - 8 categories: risk-management, data-governance, record-keeping, transparency, human-oversight, deployer-obligations, fria, documentation.
  - Helper functions: `get_requirement(id)` and `get_requirements_by_category(category)`.
- **EU AI Act evaluator** (`src/licit/frameworks/eu_ai_act/evaluator.py`)
  - `EUAIActEvaluator` with dynamic method dispatch via `getattr(self, f"_eval_{id}")` — adding new articles requires only a new method + requirement entry.
  - Dedicated evaluation methods for all 11 articles with scoring logic:
    - Art. 9: Risk management (guardrails +1, quality gates +1, budget +1, security scanning +1; compliant at 3+).
    - Art. 10: Data governance (always PARTIAL — deployer doesn't train models).
    - Art. 12: Record keeping (git +1, audit trail +2, provenance +1, OTel +1; compliant at 3+).
    - Art. 13: Transparency (Annex IV +2, changelog +1, traceability +1; compliant at 2+).
    - Art. 14: Human oversight (dry-run +1, review gate +2, quality gates +1, budget +1; compliant at 3+).
    - Art. 14(4)(a): Delegates to Art. 14(1) — same evidence applies.
    - Art. 14(4)(d): Intervention capability (dry-run + rollback → COMPLIANT).
    - Art. 26(1): Agent configs present → COMPLIANT.
    - Art. 26(5): Delegates to Art. 12(1) — monitoring = logging.
    - Art. 27: FRIA document present → COMPLIANT.
    - Annex IV: Technical documentation present → COMPLIANT.
  - `_score_to_status()` helper with configurable `compliant_at` and `partial_at` thresholds.
  - Type-safe `provenance_stats` access with `isinstance` check and `logger.debug` on unexpected types.
  - Scoring rationale documented in each method's docstring.
- **FRIA generator** (`src/licit/frameworks/eu_ai_act/fria.py`)
  - `FRIAGenerator` — Interactive 5-step questionnaire per EU AI Act Article 27.
  - 5 steps with 16 questions: System Description (5), Fundamental Rights Identification (4), Impact Assessment (3), Mitigation Measures (5), Monitoring & Review (3).
  - Auto-detection for 8 fields: system_purpose, ai_technology, models_used, human_review, guardrails, security_scanning, testing, audit_trail.
  - `_detect_models_used()` reads architect config YAML for model info with `OSError`/`YAMLError` handling.
  - `generate_report()` — Jinja2 template rendering to Markdown with `encoding="utf-8"`.
  - `save_data()` — JSON persistence for future FRIA updates.
  - Version from `licit.__version__` (not hardcoded).
- **Annex IV generator** (`src/licit/frameworks/eu_ai_act/annex_iv.py`)
  - `AnnexIVGenerator` — Auto-populates technical documentation from project metadata.
  - `_collect_data()` aggregates 27 template variables from `ProjectContext` and `EvidenceBundle`.
  - 6-section document: General Description, Development Process, Monitoring/Functioning/Control, Risk Management, Testing/Validation, Changes/Lifecycle.
  - Recommendations auto-generated for missing features (provenance, audit trail, guardrails, FRIA, security scanning, test framework).
- **Jinja2 templates** (`src/licit/frameworks/eu_ai_act/templates/`)
  - `fria_template.md.j2` — FRIA report with header table, 5 steps rendered from responses, summary, review schedule.
  - `annex_iv_template.md.j2` — Annex IV with 6 sections, conditional blocks, recommendations for gaps. Whitespace-controlled with `{%-`/`-%}` for clean output.
  - `report_section.md.j2` — Framework compliance section for Phase 6 unified report (summary table + per-requirement details).

#### QA Hardening — Phase 4

- **Bug fixes** — 2 issues found and fixed during QA review:
  - **(Medium)** `fria_template.md.j2`: `{{ responses.responsible_person }}` used direct dict attribute access inside `{% if %}` guard — changed to `{{ responses.get('responsible_person', '') }}`.
  - **(Medium)** `annex_iv_template.md.j2`: Excessive blank lines between sections due to Jinja2 whitespace handling — added `{%-`/`-%}` whitespace control on conditional blocks.
- **124 new Phase 4 tests** across 5 test files:
  - `test_evaluator.py` (32) — Properties, full evaluation, Art. 9/10/12/13/14/26/27/Annex IV compliance paths (compliant, partial, non-compliant).
  - `test_fria.py` (23) — FRIA steps structure (5 steps, keys, choices, unique fields), auto-detection (8 fields), report generation, data saving.
  - `test_annex_iv.py` (17) — File creation, content sections (12 checks), minimal project, recommendations.
  - `test_requirements.py` (9) — Data integrity, unique IDs, categories, `get_requirement()`, `get_requirements_by_category()`.
  - `test_qa_edge_cases.py` (43) — Protocol conformance (`isinstance` check), `_score_to_status` boundaries (7), evaluator edge cases (provenance_stats string/None/missing, all-compliant, all-non-compliant, delegation preserves requirement ID), FRIA edge cases (empty responses, unicode, roundtrip, YAML real/malformed/missing), Annex IV edge cases (unicode, empty, pipe chars, percentage 0/100), registry (5), CLI integration (`verify --framework eu-ai-act`), requirements integrity, cross-module compatibility (ControlResult → GapItem, ComplianceSummary).
- **CLI integration** — `licit fria`, `licit annex-iv`, and `licit verify --framework eu-ai-act` now fully functional:
  - Real imports replacing `# type: ignore[import-not-found]` stubs for EU AI Act modules.
  - `FRIAGenerator`, `AnnexIVGenerator`, `EUAIActEvaluator` use real types (not `Any`).
- **Test infrastructure** — `conftest.py` updated:
  - `make_context()` now accepts `security: SecurityTooling | None` parameter.
  - `make_evidence()` now accepts `provenance_stats`, `fria_path`, `annex_iv_path`, `audit_entry_count`, `changelog_entry_count` parameters.

### Changed

- Test suite expanded from 373 to 497 tests (373 previous + 124 Phase 4).
- `licit fria`, `licit annex-iv` commands now fully functional (were skeletons in Phase 1).
- `licit verify --framework eu-ai-act` now evaluates 11 articles and returns exit codes 0/1/2.
- CLI imports for EU AI Act modules changed from lazy `type: ignore` stubs to real imports.
- `pyproject.toml` version bumped to `0.4.0`.

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
