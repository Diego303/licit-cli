# licit

**Regulatory compliance for AI-powered development teams.**

licit is a standalone CLI tool that tracks AI-generated code provenance, evaluates compliance against regulatory frameworks (EU AI Act, OWASP Agentic Top 10), generates required documentation (FRIA, Annex IV), and works as a CI/CD gate — all without requiring external services or infrastructure.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## The Problem

Teams using AI coding assistants (Claude Code, Cursor, Copilot, Codex) face three gaps:

1. **No provenance tracking** — Can't distinguish AI-generated code from human-written code at scale.
2. **Regulatory requirements** — The EU AI Act mandates documentation (FRIA, Annex IV), risk management, and transparency that no existing tool automates.
3. **Agentic security risks** — Autonomous AI agents introduce risks (prompt injection, privilege escalation) not covered by traditional security tools.

## The Solution

```
licit init       →  Auto-detect project: languages, frameworks, CI/CD, agent configs
licit trace      →  Track code provenance (human vs AI) from git history
licit changelog  →  Monitor agent config changes (CLAUDE.md, .cursorrules, etc.)
licit fria       →  Generate Fundamental Rights Impact Assessment (EU AI Act Art. 27)
licit annex-iv   →  Generate Annex IV Technical Documentation
licit report     →  Unified compliance report (Markdown, JSON, HTML)
licit gaps       →  Find compliance gaps with actionable recommendations
licit verify     →  CI/CD gate: exit 0 (pass) or exit 1 (fail)
licit status     →  Quick compliance overview
licit connect    →  Configure optional connectors (architect, vigil)
```

## Quick Start

### Installation

```bash
pip install licit-ai-cli
```

Or from source:

```bash
git clone https://github.com/Diego303/licit-cli.git
cd licit-cli
pip install -e ".[dev]"
```

> **Requires Python 3.12+**

### Initialize

```bash
cd your-project
licit init
```

This auto-detects your project and creates `.licit.yaml`:

```
  Project: my-app
  Languages: python, typescript
  Agent configs: 2 detected
  CI/CD: github-actions
  Testing: pytest
  Security tools: vigil, semgrep

  Agent configurations found:
    - CLAUDE.md (claude-code)
    - .cursorrules (cursor)

  Created .licit.yaml
  Created .licit/ directory
```

### Track Provenance

```bash
licit trace                      # Analyze full git history
licit trace --since 2026-01-01   # Since specific date
licit trace --stats              # Show AI vs human stats
licit trace --report             # Generate Markdown report
```

Output example:

```
  Analyzing git history...
  Records: 45 files analyzed
  AI-generated: 18 (40.0%)
  Human-written: 22 (48.9%)
  Mixed: 5 (11.1%)

  AI tools detected: claude-code (15), cursor (3)
  Models detected: claude-sonnet-4 (12), claude-opus-4 (3), gpt-4o (3)

  Stored in .licit/provenance.jsonl
```

### Evaluate Compliance

```bash
licit report                         # Full compliance report
licit report --framework eu-ai-act   # EU AI Act only
licit report --format html -o r.html # HTML output
licit gaps                           # What's missing?
```

### CI/CD Integration

```yaml
# .github/workflows/compliance.yml
- name: Compliance check
  run: |
    pip install licit-ai-cli
    licit verify
```

Exit codes: `0` = compliant, `1` = non-compliant, `2` = partially compliant.

## Frameworks Supported

| Framework | Version | Status |
|-----------|---------|--------|
| EU AI Act | Regulation (EU) 2024/1689 | V0 |
| OWASP Agentic Top 10 | 2026 | V0 |
| NIST AI RMF | AI 100-1 | Planned (V1) |
| ISO/IEC 42001 | 2023 | Planned (V1) |

### EU AI Act Coverage

licit evaluates deployer obligations across key articles:

- **Art. 9** — Risk management (guardrails, quality gates, security scanning)
- **Art. 12** — Record keeping (git history, audit trails, provenance)
- **Art. 13** — Transparency (technical documentation, config changelog)
- **Art. 14** — Human oversight (review gates, dry-run, intervention capability)
- **Art. 26** — Deployer obligations (agent configuration, monitoring)
- **Art. 27** — FRIA (interactive 5-step questionnaire)
- **Annex IV** — Technical documentation (auto-generated from project metadata)

### OWASP Agentic Top 10 Coverage

Maps project security posture against all 10 agentic AI risks including prompt injection, unauthorized code execution, data exfiltration, and privilege escalation.

## Agent Configs Detected

licit monitors configuration files for AI coding agents:

| File | Agent |
|------|-------|
| `CLAUDE.md` | Claude Code |
| `.claude/settings.json` | Claude Code |
| `.cursorrules` | Cursor |
| `.cursor/rules` | Cursor |
| `AGENTS.md` | GitHub Agents |
| `.github/copilot-instructions.md` | GitHub Copilot |
| `.architect/config.yaml` | architect |
| `.prompts/**/*.md` | Generic |

## Provenance Tracking

licit uses a multi-method approach to determine code provenance:

### Methods

| Method | How it works | Confidence |
|--------|-------------|------------|
| `git-infer` | 6-heuristic scoring of git commits (author, message, bulk, co-authors, file patterns, time) | 60-95% |
| `session-log` | Parse agent session files (Claude Code JSONL logs) | 95% |

### Heuristics Engine

The git-infer method applies 6 weighted heuristics to each commit:

1. **Author pattern** (weight 3.0) — Known AI agent names (claude, copilot, cursor, devin, bot)
2. **Message pattern** (weight 1.5) — Conventional commits, "implement", "generated by", `[ai]`/`[bot]`
3. **Bulk changes** (weight 2.0) — Large file/line counts typical of AI generation
4. **Co-author trailer** (weight 3.0) — `Co-authored-by:` with AI keywords
5. **File patterns** (weight 1.0) — All files are test files
6. **Time pattern** (weight 0.5) — Commits between 1am-5am

Only heuristics that fire (score > 0) contribute to the weighted average, preventing silent heuristics from diluting strong signals.

### Cryptographic Attestation

Provenance records can be cryptographically signed:

```yaml
provenance:
  sign: true                              # Enable HMAC-SHA256 signing
  sign_key_path: /path/to/key             # Optional: explicit key path
  # Default: auto-generates .licit/.signing-key
```

- Individual records signed with HMAC-SHA256
- Batch records signed with Merkle tree (root hash)
- Timing-safe verification via `hmac.compare_digest`

## Agent Config Changelog

licit tracks changes to AI agent configuration files across git history, producing semantic diffs with severity classification.

```bash
licit changelog                        # Generate changelog (Markdown)
licit changelog --format json          # JSON output
licit changelog --since 2026-01-01     # Since specific date
```

### Pipeline

```
ConfigWatcher → Semantic Differ → Change Classifier → Renderer
  (git log)     (YAML/JSON/MD)    (MAJOR/MINOR/PATCH)  (MD/JSON)
```

### Severity Classification

| Severity | Trigger | Examples |
|----------|---------|----------|
| **MAJOR** | Model/provider change, or removal of a MINOR field | `model: gpt-4` → `model: gpt-5`, removing `guardrails` |
| **MINOR** | Prompt, guardrails, tools, rules, or markdown section changes | Editing `system_prompt`, adding `blocked_commands` |
| **PATCH** | Everything else | Parameter tweaks, formatting, comments |

### Supported Formats

| Format | Diff Strategy |
|--------|--------------|
| YAML (`.yaml`, `.yml`) | Recursive key-value diff with nested dict support |
| JSON (`.json`) | Recursive key-value diff |
| Markdown (`.md`) | Section-aware diff (by headings), with fenced code block awareness |
| Plain text | Whole-file line diff |

## Configuration

All configuration lives in `.licit.yaml`:

```yaml
provenance:
  enabled: true
  methods: [git-infer, session-log]       # Methods to use
  session_dirs: []                         # Custom session log directories
  confidence_threshold: 0.6               # Minimum confidence (0.0-1.0)
  sign: false                             # HMAC-SHA256 signing
  sign_key_path: null                     # Custom key path (auto-generates if null)
  store_path: .licit/provenance.jsonl     # Append-only JSONL store

changelog:
  enabled: true
  watch_files:
    - CLAUDE.md
    - .cursorrules
    - AGENTS.md
    - .architect/config.yaml

frameworks:
  eu_ai_act: true
  owasp_agentic: true

connectors:
  architect:
    enabled: false
  vigil:
    enabled: false

reports:
  default_format: markdown
  include_evidence: true
  include_recommendations: true
```

## Optional Connectors

licit is **fully standalone** — connectors enrich, they don't enable.

| Connector | What it reads | Value added |
|-----------|--------------|-------------|
| **architect** | `.architect/reports/`, config | Guardrails, quality gates, budget limits, audit trail |
| **vigil** | SARIF files | Security findings with severity levels |

```bash
licit connect architect --enable
licit connect vigil --enable
```

## Project Structure

```
src/licit/
├── cli.py                              # 10 CLI commands (Click)
├── config/                             # Pydantic v2 config schema + YAML loader
├── core/                               # Models, project detection, evidence collection
├── provenance/                         # ✅ Phase 2 — complete
│   ├── heuristics.py                   # 6-heuristic AI commit scoring engine
│   ├── git_analyzer.py                 # Git history analysis + agent/model inference
│   ├── store.py                        # Append-only JSONL provenance store
│   ├── attestation.py                  # HMAC-SHA256 signing + Merkle tree
│   ├── tracker.py                      # Orchestrator (git + sessions + sign + store)
│   ├── report.py                       # Markdown report generator
│   └── session_readers/                # Agent session log parsers
│       ├── base.py                     # SessionReader Protocol
│       └── claude_code.py              # Claude Code JSONL reader
├── changelog/                          # ✅ Phase 3 — complete
│   ├── watcher.py                     # Git history tracking of config files
│   ├── differ.py                      # Semantic diff (YAML/JSON/MD/text)
│   ├── classifier.py                  # Severity classification (MAJOR/MINOR/PATCH)
│   └── renderer.py                    # Markdown + JSON output
├── frameworks/                         # EU AI Act, OWASP (Phase 4-5)
├── connectors/                         # architect + vigil (Phase 7)
├── reports/                            # Unified reports, gap analysis (Phase 6)
└── logging/                            # structlog configuration
```

## Documentation

Full documentation (in Spanish) is available in the [`docs/`](docs/) directory:

- [Quick start](docs/inicio-rapido.md) — Get licit running in 5 minutes
- [Architecture](docs/arquitectura.md) — System design, modules, and phases
- [CLI guide](docs/guia-cli.md) — Complete command reference
- [Configuration](docs/configuracion.md) — All `.licit.yaml` fields
- [Data models](docs/modelos.md) — Enums, dataclasses, and Pydantic schemas
- [Security](docs/seguridad.md) — Threat model, signing, data protection
- [Compliance](docs/compliance.md) — EU AI Act and OWASP framework details
- [Best practices](docs/buenas-practicas.md) — Integration recommendations
- [Development](docs/desarrollo.md) — Contributing guide
- [FAQ](docs/faq.md) — Troubleshooting and common questions

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests (373 tests)
pytest tests/ -q

# Lint
ruff check src/licit/

# Type check
mypy src/licit/ --strict
```

## Philosophy

- **Standalone** — Works without any external tools. Connectors are optional.
- **Filesystem-first** — Everything is files in `.licit/`. No database, no server.
- **Developer-first** — CLI that fits into existing git/CI workflows.
- **Language-agnostic** — Detects Python, JS/TS, Go, Rust, Java projects.
- **Provenance-first** — Understands code origin (AI vs human) for more accurate evaluations.

## Roadmap

| Version | Key Features |
|---------|-------------|
| **V0** (current) | CLI, provenance tracking (git + Claude Code sessions), EU AI Act, OWASP, FRIA, Annex IV, CI/CD gate |
| **V0.x** | Cursor/Codex session readers, PDF reports, GitHub Action |
| **V1** | NIST AI RMF, ISO 42001, plugin system, Sigstore, MCP Server |
| **V2** | Web dashboard, multi-project, trend analysis, AI remediation |

## License

[MIT](LICENSE) — Copyright (c) 2026 Diego Alba Ruiz
