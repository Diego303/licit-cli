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

## Configuration

All configuration lives in `.licit.yaml`:

```yaml
provenance:
  enabled: true
  methods: [git-infer]
  confidence_threshold: 0.6
  store_path: .licit/provenance.jsonl

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
├── cli.py              # 10 CLI commands
├── config/             # Pydantic v2 config schema + YAML loader
├── core/               # Models, project detection, evidence collection
├── provenance/         # Git analysis, heuristics, JSONL store, attestation
├── changelog/          # Agent config monitoring, diff, classification
├── frameworks/         # EU AI Act evaluator, FRIA, Annex IV, OWASP
├── connectors/         # architect + vigil integrations
├── reports/            # Unified reports, gap analysis, formatters
└── logging/            # structlog configuration
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

# Run tests (113 tests)
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
| **V0** (current) | CLI, EU AI Act, OWASP, provenance, FRIA, Annex IV, CI/CD gate |
| **V0.x** | Cursor/Codex session readers, PDF reports, GitHub Action |
| **V1** | NIST AI RMF, ISO 42001, plugin system, Sigstore, MCP Server |
| **V2** | Web dashboard, multi-project, trend analysis, AI remediation |

## License

[MIT](LICENSE) — Copyright (c) 2026 Diego Alba Ruiz
