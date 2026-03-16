# Seguimiento de Implementación — licit V1

> Documento de seguimiento para el desarrollo post-v1.0.0.
> Para el historial detallado de implementación del MVP (fases 1-7), ver [SEGUIMIENTO-V0.md](SEGUIMIENTO-V0.md).

---

## Resumen de V1.0.0 (baseline)

licit v1.0.0 es la primera release estable. Incluye 7 fases de implementación + un QA exhaustivo con 142 tests manuales sobre 5 proyectos simulados.

### Lo que está implementado

| Módulo | Descripción | Archivos |
|--------|-------------|----------|
| **Config** | Schema Pydantic v2 (9 modelos), loader YAML con fallback + warnings visibles, save | 3 source |
| **Core** | Models (3 enums + 6 dataclasses), ProjectDetector (8 detectores), EvidenceCollector (18 campos) | 3 source |
| **Provenance** | GitAnalyzer (6 heurísticas, filtro por author date), store JSONL deduplicado, attestation HMAC-SHA256 + Merkle, tracker, session reader Claude Code, report generator | 8 source |
| **Changelog** | ConfigWatcher (git history), semantic differ (YAML/JSON/MD/text), classifier (MAJOR/MINOR/PATCH), renderer (Markdown/JSON con extensión correcta) | 4 source |
| **EU AI Act** | 11 requirements, evaluator (11 artículos), FRIA generator (5 pasos, 16 preguntas, auto-detect, modo `--auto`), Annex IV generator, 3 templates Jinja2 | 5 source + 3 templates |
| **OWASP Agentic** | 10 requirements (ASI01-ASI10), evaluator (10 controles), 1 template Jinja2 | 3 source + 1 template |
| **Reports** | UnifiedReportGenerator, GapAnalyzer (tool suggestions + effort), renderers Markdown/JSON/HTML (self-contained), terminal summary con progress bars | 6 source |
| **Connectors** | Connector Protocol, ArchitectConnector (reports/audit/config), VigilConnector (SARIF/SBOM), EvidenceCollector con delegación a connectors | 3 source |
| **CLI** | 10 comandos (init, trace, changelog, fria, annex-iv, report, gaps, verify, status, connect), opciones globales (--version, --config, --verbose) | 1 source (620 líneas) |
| **Logging** | structlog (WARNING default, DEBUG con --verbose) | 1 source |

### Números

| Métrica | Valor |
|---------|-------|
| Source files | 50 (.py) + 4 (.j2 templates) |
| Test files | 50 |
| Tests | 789 |
| CLI commands | 10 |
| EU AI Act requirements | 11 (Art. 9, 10, 12, 13, 14, 14(4)(a), 14(4)(d), 26, 26(5), 27, Annex IV) |
| OWASP requirements | 10 (ASI01–ASI10) |
| Heurísticas provenance | 6 (author, message, bulk, co-author, file pattern, time) |
| Agent configs detectados | 10 patrones (CLAUDE.md, .cursorrules, AGENTS.md, copilot-instructions, architect, etc.) |
| Lenguajes detectados | 6 (Python, JS, TS, Go, Rust, Java) |
| Formatos de reporte | 3 (Markdown, JSON, HTML) |
| Connectors | 2 (architect, vigil) |

### Bugs corregidos en QA V0 (pre-release)

| Severidad | Descripción |
|-----------|-------------|
| CRITICAL | `trace --since` no filtraba (git committer date vs author date) |
| CRITICAL | Crash PermissionError sin manejo en store |
| HIGH | Store crecía indefinidamente (append sin dedup) |
| HIGH | Discrepancia numérica trace vs stats |
| MEDIUM × 4 | changelog JSON en .md, output_dir ignorado, init sin aviso, gaps misleading |
| LOW | Config errors invisibles sin --verbose |
| FEATURE | `fria --auto` para CI/CD |

### Calidad

- `pytest tests/ -q` — 789 tests, todos pasan
- `ruff check src/licit/` — 0 errores
- `mypy src/licit/ --strict` — 0 issues (50 archivos)
- QA exhaustivo: 142 tests manuales, 0 bugs pendientes
- Documentación: 25 archivos en `docs/`, README completo, CHANGELOG detallado

---

## Backlog V1.x

Funcionalidades planificadas para releases incrementales post-v1.0.0.

| ID | Descripción | Prioridad | Esfuerzo |
|----|-------------|-----------|----------|
| V1.1 | Session readers para Cursor y Codex | Alta | Media |
| V1.2 | Generación de reportes PDF | Media | Media |
| V1.3 | GitHub Action oficial (`licit-action`) | Alta | Baja |
| V1.4 | Connectors adicionales (Semgrep SARIF nativo, Snyk, GitHub API) | Media | Alta |
| V1.5 | Threshold configurable para `verify` exit codes (`--min-score`) | Media | Baja |
| V1.6 | Comando `licit clean` para resetear datos | Baja | Baja |
| V1.7 | Auto-add `.licit/` a `.gitignore` en `init` | Baja | Baja |

---

## Desarrollo en curso

> Esta sección se actualiza conforme se trabaja en nuevas funcionalidades.

(Nada en curso — v1.0.0 recién publicada)

---

## Historial de releases

| Versión | Fecha | Highlights |
|---------|-------|------------|
| v1.0.0 | 2026-03-16 | Release estable. QA exhaustivo, 10 bug fixes, `fria --auto`, store deduplicado |
| v0.7.0 | 2026-03-15 | Connectors (architect + vigil), integration tests |
| v0.6.0 | 2026-03-15 | Reports (Markdown/JSON/HTML), gap analyzer, terminal summary |
| v0.5.0 | 2026-03-14 | OWASP Agentic Top 10 (10 requirements + evaluator) |
| v0.4.0 | 2026-03-14 | EU AI Act (11 articles + FRIA + Annex IV) |
| v0.3.0 | 2026-03-13 | Changelog (watcher + differ + classifier + renderer) |
| v0.2.0 | 2026-03-11 | Foundation + Provenance (heuristics + git analyzer + store + attestation) |
| v0.1.0 | 2026-03-10 | Initial release (config + project detection + CLI skeleton) |
