# Arquitectura

## Visión general

licit es una herramienta CLI standalone que analiza proyectos de desarrollo asistido por IA para evaluar su compliance regulatorio. Opera de forma local (filesystem-first), sin requerir servicios externos ni bases de datos.

```
licit (CLI)
├── config/          Esquema Pydantic v2 + loader YAML
├── core/            Modelos de dominio + detección + evidencia
├── logging/         structlog configuración
├── provenance/      Trazabilidad de código (Fase 2 — COMPLETADA)
├── changelog/       Registro de cambios en configs de agentes (Fase 3 — COMPLETADA)
├── frameworks/      Evaluadores regulatorios (Fases 4-5 COMPLETADAS)
│   ├── base.py          Protocol ComplianceFramework
│   ├── registry.py      Registro de frameworks
│   ├── eu_ai_act/   EU AI Act (Fase 4 — COMPLETADA)
│   └── owasp_agentic/  OWASP Agentic Top 10 (Fase 5 — COMPLETADA)
├── reports/         Reportes + gap analysis (Fase 6 — COMPLETADA)
└── connectors/      Integraciones opcionales (Fase 7 — COMPLETADA)
```

## Stack tecnológico

| Componente | Tecnología | Justificación |
|---|---|---|
| CLI | Click 8.1+ | Composición de comandos, tipos, ayuda automática |
| Validación de config | Pydantic v2 | Validación estricta, serialización YAML/JSON |
| Modelos de dominio | dataclasses | Ligeros, sin dependencias, tipado nativo |
| Enums | StrEnum (Python 3.12) | Serialización directa a string, compatible con ruff UP042 |
| Logging | structlog | Logging estructurado, procesadores componibles |
| Config | PyYAML | Estándar de facto para config en YAML |
| Templates | Jinja2 | Generación de reportes Markdown/HTML |
| Crypto | cryptography | HMAC-SHA256 para firmas de provenance |

## Principios de diseño

1. **Filesystem-first**: Toda la data se almacena en `.licit/` dentro del proyecto. No hay bases de datos, APIs ni servicios remotos.

2. **Dataclasses para dominio, Pydantic para config**: Los modelos de dominio (`ProvenanceRecord`, `ControlResult`, etc.) son dataclasses puros. Solo la configuración (`LicitConfig`) usa Pydantic v2.

3. **Protocol para interfaces**: Las abstracciones entre módulos usan `typing.Protocol`, no herencia con clases abstractas.

4. **Imports directos**: Todos los módulos usan imports directos. Los connectors usan `TYPE_CHECKING` guards para evitar imports circulares con `EvidenceBundle`.

5. **Detección automática**: `ProjectDetector` infiere lenguajes, frameworks, CI/CD, herramientas de seguridad y configuraciones de agentes IA sin necesidad de configuración manual.

## Flujo de datos

```
Proyecto del usuario
       │
       ├──────────────────────────────────────┬─────────────────────┐
       ▼                                      ▼                     ▼
┌─────────────────┐                  ┌──────────────────┐  ┌───────────────────┐
│ ProjectDetector  │                  │ProvenanceTracker  │  │  ConfigWatcher     │
│                  │                  │                    │  │                    │
│ Detecta lenguajes│                  │ ┌──────────────┐  │  │ git log --follow   │
│ frameworks, CI/CD│                  │ │ GitAnalyzer   │  │  │ → ConfigSnapshot[] │
│ agentes          │                  │ │  + Heuristics │  │  └────────┬──────────┘
└────────┬────────┘                  │ └──────┬───────┘  │           │
         │ ProjectContext             │        │          │  ┌────────▼──────────┐
         ▼                           │ ┌──────────────┐  │  │  Semantic Differ   │
┌─────────────────┐                  │ │SessionReaders │  │  │  (YAML/JSON/MD)    │
│EvidenceCollector │                  │ └──────┬───────┘  │  └────────┬──────────┘
│                  │                  │        │          │           │ FieldDiff[]
│ .licit/, configs │                  │ ┌──────────────┐  │  ┌────────▼──────────┐
│ SARIF, architect │                  │ │  Attestor    │  │  │ ChangeClassifier   │
└────────┬────────┘                  │ └──────┬───────┘  │  │ (MAJOR/MINOR/PATCH)│
         │ EvidenceBundle             │        │          │  └────────┬──────────┘
         ▼                           │ ┌──────────────┐  │           │ ConfigChange[]
┌─────────────────┐                  │ │    Store     │  │  ┌────────▼──────────┐
│   Evaluadores   │ ← Fases 4-5     │ └──────────────┘  │  │ ChangelogRenderer  │
└────────┬────────┘                  └──────────┬───────┘  │ (Markdown / JSON)  │
         │ ControlResult[]                      │          └────────┬──────────┘
         ▼                                      ▼                   ▼
┌─────────────────┐                  ┌──────────────────┐  ┌───────────────────┐
│   Reportes      │ ← Fase 6        │ Provenance Report │  │ changelog.md/json  │
└─────────────────┘                  └──────────────────┘  └───────────────────┘
```

## Módulos implementados (Fases 1-7)

### config/ — Configuración

- **`schema.py`**: 9 modelos Pydantic v2 con clase raíz `LicitConfig`. Todos los campos tienen defaults sensatos.
- **`loader.py`**: Carga configuración con resolución en 3 niveles: path explícito → `.licit.yaml` en cwd → defaults.
- **`defaults.py`**: Constantes: `CONFIG_FILENAME`, `DATA_DIR`, instancia `DEFAULTS`.

### core/ — Núcleo

- **`models.py`**: 3 enums (`ComplianceStatus`, `ChangeSeverity`, `ProvenanceSource`) y 6 dataclasses (`ProvenanceRecord`, `ConfigChange`, `ControlRequirement`, `ControlResult`, `ComplianceSummary`, `GapItem`).
- **`project.py`**: `ProjectDetector` con 8 métodos de detección. Produce un `ProjectContext` completo.
- **`evidence.py`**: `EvidenceCollector` que delega a connectors formales (con config) o inline temporales (sin config). Produce un `EvidenceBundle` con 18 campos. Acepta `LicitConfig` opcional para activar connectors.

### logging/ — Logging

- **`setup.py`**: Configura structlog con `WriteLoggerFactory`, nivel WARNING por defecto (DEBUG con `--verbose`).

### provenance/ — Trazabilidad de código

- **`heuristics.py`**: Motor de 6 heurísticas para detectar commits AI (author, message, bulk, co-author, file patterns, time). Promedio ponderado de solo heurísticas señalizantes. Soporta custom patterns desde JSON.
- **`git_analyzer.py`**: Parsea `git log` con separadores `\x00`/`\x01` para robustez. `CommitInfo` dataclass. Inferencia de agente (8 patrones) y modelo (8 regex). Clasificación: >=0.7 → "ai", >=0.5 → "mixed", <0.5 → "human".
- **`store.py`**: Store append-only JSONL. Operaciones: `append()`, `load_all()`, `get_stats()`, `get_by_file()`. Deduplicación por último timestamp.
- **`attestation.py`**: HMAC-SHA256 para firmado individual, Merkle tree para firmado batch. Key management con generación automática.
- **`tracker.py`**: Orquestador que combina git analysis + session reading + confidence filtering + signing + store.
- **`report.py`**: Generador de reportes Markdown con summary, AI tools, models, file details.
- **`session_readers/base.py`**: Protocol `SessionReader` para extensibilidad.
- **`session_readers/claude_code.py`**: Lee sesiones Claude Code (JSONL) de `~/.claude/projects/`.

### changelog/ — Changelog de configs de agentes

- **`watcher.py`**: `ConfigWatcher` monitorea archivos de configuración a través del historial de git. `ConfigSnapshot` dataclass. Size guard de 1 MB, timeouts explícitos, deduplicación.
- **`differ.py`**: Diffing semántico por formato: YAML/JSON (dict recursivo), Markdown (secciones con code block awareness), texto plano. `FieldDiff` dataclass. `_coerce_to_dict()` para roots no-dict.
- **`classifier.py`**: Clasificación MAJOR/MINOR/PATCH con matching por segmentos (`_field_matches`). Escalación por eliminación. Timestamps UTC.
- **`renderer.py`**: Rendering en Markdown (agrupado por archivo, ordenado por severidad) y JSON (`ensure_ascii=False`).

### frameworks/ — Evaluadores de compliance

- **`base.py`**: Protocol `ComplianceFramework` (`@runtime_checkable`). Define interfaz: `name`, `version`, `description`, `get_requirements()`, `evaluate()`.
- **`registry.py`**: `FrameworkRegistry` — registro global con `register()`, `get()`, `list_all()`. Singleton via `get_registry()`.
- **`eu_ai_act/requirements.py`**: 11 `ControlRequirement` (Art. 9, 10, 12, 13, 14, 14(4)(a), 14(4)(d), 26, 26(5), 27, Annex IV). Helpers: `get_requirement()`, `get_requirements_by_category()`.
- **`eu_ai_act/evaluator.py`**: `EUAIActEvaluator` — dispatch dinámico via `getattr(self, f"_eval_{id}")`. Scoring por artículo con `_score_to_status(score, compliant_at, partial_at)`.
- **`eu_ai_act/fria.py`**: `FRIAGenerator` — cuestionario interactivo de 5 pasos, 16 preguntas, auto-detección de 8 campos, generación de reporte Jinja2.
- **`eu_ai_act/annex_iv.py`**: `AnnexIVGenerator` — auto-puebla documentación técnica desde metadatos del proyecto (27 variables de template).
- **`eu_ai_act/templates/`**: 3 templates Jinja2 (FRIA report, Annex IV, report section).
- **`owasp_agentic/requirements.py`**: 10 `ControlRequirement` (ASI01–ASI10). 10 categorías: access-control, input-security, supply-chain, observability, output-security, human-oversight, isolation, resource-limits, error-handling, data-protection.
- **`owasp_agentic/evaluator.py`**: `OWASPAgenticEvaluator` — dispatch dinámico via `getattr(self, f"_eval_{id}")`. Scoring por control con thresholds variables (ASI08/ASI09 usan `compliant_at=2`, el resto `compliant_at=3`). Helpers: `_score_to_status()`, `_safe_float()`.
- **`owasp_agentic/templates/`**: 1 template Jinja2 (report section, alineado con EU AI Act).

### reports/ — Reportes y análisis de brechas

- **`unified.py`**: `UnifiedReportGenerator` — orquesta evaluación multi-framework, produce `UnifiedReport` con estadísticas agregadas. Exception-safe: un framework que falla se skipea sin romper el reporte.
- **`gap_analyzer.py`**: `GapAnalyzer` — identifica requisitos `NON_COMPLIANT` y `PARTIAL`, genera `GapItem` con tool suggestions y effort estimates. 17 categorías mapeadas (8 EU AI Act + 10 OWASP, `human-oversight` compartida).
- **`markdown.py`**: Renderiza `UnifiedReport` como Markdown con tablas de resumen, iconos de estado (`[PASS]`/`[FAIL]`/`[PARTIAL]`), evidence y recommendations condicionales.
- **`json_fmt.py`**: Renderiza como JSON estructurado con `ensure_ascii=False` para unicode.
- **`html.py`**: Renderiza como HTML auto-contenido (sin CSS/JS externos). Badges de color por status. XSS-safe: escapa 5 caracteres (`&`, `<`, `>`, `"`, `'`).
- **`summary.py`**: `print_summary()` imprime resumen compacto con barras de progreso ASCII al terminal.

### connectors/ — Integraciones opcionales

- **`base.py`**: Protocol `Connector` (`@runtime_checkable`). Define interfaz: `name`, `enabled`, `available()`, `collect(evidence)`. `ConnectorResult` dataclass con `success` computado (`files_read > 0 and no errors`).
- **`architect.py`**: `ArchitectConnector` — lee 3 fuentes: reports JSON (`_read_reports`), audit JSONL (`_read_audit_log`), config YAML (`_read_config`). Extrae guardrails, quality gates, budget, dry-run/rollback. `guardrail_count` es aditivo (`+=`).
- **`vigil.py`**: `VigilConnector` — parsea SARIF 2.1.0 con 4 métodos (`_parse_run`, `_extract_tool_name`, `_parse_finding`, `_extract_location`). Lee SBOM CycloneDX. `_resolve_sarif_paths` soporta archivo, directorio, y auto-detected con deduplicación.

### cli.py — Interfaz de línea de comandos

10 comandos registrados con Click, todos funcionales. `report` genera reportes en 3 formatos (Markdown, JSON, HTML). `gaps` muestra brechas con recomendaciones y herramientas sugeridas. `verify` evalúa EU AI Act + OWASP Agentic Top 10 y retorna exit codes para CI/CD. `connect` muestra disponibilidad de datos al habilitar un connector.

## Fases de implementación

| Fase | Módulo | Estado | Descripción |
|---|---|---|---|
| 1 | Foundation | **COMPLETADA** | Config, modelos, detección, evidencia, CLI, logging |
| 2 | Provenance | **COMPLETADA** | git_analyzer, heuristics, store JSONL, HMAC, attestation, session readers, report |
| 3 | Changelog | **COMPLETADA** | watcher, differ semántico, classifier (MAJOR/MINOR/PATCH), renderer (MD/JSON) |
| 4 | EU AI Act | **COMPLETADA** | Protocol, registry, evaluador (11 artículos), FRIA interactivo, Annex IV, templates Jinja2 |
| 5 | OWASP | **COMPLETADA** | Evaluador OWASP Agentic Top 10 (10 controles), scoring por riesgo, template Jinja2 |
| 6 | Reports | **COMPLETADA** | Reporte unificado, gap analyzer, Markdown/JSON/HTML, terminal summary |
| 7 | Connectors | **COMPLETADA** | Protocol Connector, ArchitectConnector, VigilConnector, integration tests |

## Grafo de dependencias

```
Phase 1: config ← core/models
         core/project (independiente)
         core/evidence ← config + core/models + (provenance.store opcional)
         cli ← config + core/* + logging

Phase 2: provenance ← core/models + config (COMPLETADA)
         provenance/heuristics (independiente)
         provenance/git_analyzer ← heuristics + core/models
         provenance/store ← core/models
         provenance/attestation (independiente)
         provenance/session_readers ← core/models
         provenance/tracker ← git_analyzer + session_readers + attestation + store + config
         provenance/report ← core/models
Phase 3: changelog ← core/models + config (COMPLETADA)
         changelog/watcher ← subprocess (git)
         changelog/differ ← yaml + json (independiente)
         changelog/classifier ← differ + core/models
         changelog/renderer ← core/models
Phase 4: frameworks/eu_ai_act ← core/* + evidence (COMPLETADA)
         frameworks/base.py (independiente — Protocol)
         frameworks/registry.py ← base.py
         eu_ai_act/requirements.py ← core/models
         eu_ai_act/evaluator.py ← requirements + core/* + evidence
         eu_ai_act/fria.py ← core/project + core/evidence + jinja2
         eu_ai_act/annex_iv.py ← core/project + core/evidence + jinja2
Phase 5: frameworks/owasp ← core/* + evidence + frameworks/base (COMPLETADA)
         owasp_agentic/requirements.py ← core/models
         owasp_agentic/evaluator.py ← requirements + core/* + evidence
Phase 6: reports ← frameworks/* + evidence + core/models (COMPLETADA)
         reports/unified ← frameworks/base + core/models + config
         reports/gap_analyzer ← core/models + config
         reports/markdown, json_fmt, html ← reports/unified
         reports/summary ← reports/unified + click
Phase 7: connectors ← config + core/evidence (COMPLETADA)
         connectors/base (independiente — Protocol + ConnectorResult)
         connectors/architect ← config.schema + base (TYPE_CHECKING: evidence)
         connectors/vigil ← config.schema + base (TYPE_CHECKING: evidence)
         core/evidence ← connectors/architect + connectors/vigil (inline delegation)
```

## Estructura de directorios del proyecto

```
licit-cli/
├── pyproject.toml              # Metadata, deps, herramientas
├── LICENSE                     # MIT
├── README.md                   # README en inglés
├── CHANGELOG.md                # Changelog en inglés
├── SECURITY.md                 # Política de seguridad
├── SEGUIMIENTO-V0.md           # Seguimiento de implementación (español)
├── docs/                       # Esta documentación
├── src/
│   └── licit/
│       ├── __init__.py         # __version__
│       ├── __main__.py         # python -m licit
│       ├── py.typed            # PEP 561
│       ├── cli.py              # Click CLI
│       ├── config/
│       │   ├── schema.py       # Modelos Pydantic
│       │   ├── loader.py       # Carga/guardado YAML
│       │   └── defaults.py     # Constantes
│       ├── core/
│       │   ├── models.py       # Dataclasses + enums
│       │   ├── project.py      # ProjectDetector
│       │   └── evidence.py     # EvidenceCollector
│       ├── logging/
│       │   └── setup.py        # structlog config
│       ├── provenance/         # Fase 2 (COMPLETADA)
│       │   ├── heuristics.py   # 6 heurísticas de detección AI
│       │   ├── git_analyzer.py # Análisis de git history
│       │   ├── store.py        # Store JSONL append-only
│       │   ├── attestation.py  # HMAC-SHA256 + Merkle tree
│       │   ├── tracker.py      # Orquestador
│       │   ├── report.py       # Generador de reportes Markdown
│       │   └── session_readers/
│       │       ├── base.py     # Protocol SessionReader
│       │       └── claude_code.py  # Reader Claude Code JSONL
│       ├── changelog/          # Fase 3 (COMPLETADA)
│       │   ├── watcher.py      # Monitoreo git de configs de agentes
│       │   ├── differ.py       # Diffing semántico (YAML/JSON/MD/text)
│       │   ├── classifier.py   # Clasificación MAJOR/MINOR/PATCH
│       │   └── renderer.py     # Rendering Markdown + JSON
│       ├── frameworks/         # Fases 4-5 (COMPLETADAS)
│       │   ├── base.py        # Protocol ComplianceFramework
│       │   ├── registry.py    # FrameworkRegistry
│       │   ├── eu_ai_act/     # EU AI Act (Fase 4)
│       │   │   ├── requirements.py  # 11 requisitos evaluables
│       │   │   ├── evaluator.py     # Evaluador por artículo
│       │   │   ├── fria.py          # Generador FRIA interactivo
│       │   │   ├── annex_iv.py      # Generador Annex IV
│       │   │   └── templates/       # Jinja2 (FRIA, Annex IV, report section)
│       │   └── owasp_agentic/ # OWASP Agentic Top 10 (Fase 5)
│       │       ├── requirements.py  # 10 riesgos como ControlRequirements
│       │       ├── evaluator.py     # Evaluador por riesgo de seguridad
│       │       └── templates/       # Jinja2 (report section)
│       ├── reports/            # Fase 6 (COMPLETADA)
│       │   ├── unified.py     # Generador de reporte multi-framework
│       │   ├── gap_analyzer.py # Análisis de brechas con recomendaciones
│       │   ├── markdown.py    # Renderer Markdown
│       │   ├── json_fmt.py    # Renderer JSON
│       │   ├── html.py        # Renderer HTML auto-contenido
│       │   └── summary.py     # Resumen terminal con barras de progreso
│       └── connectors/         # Fase 7 (COMPLETADA)
│           ├── base.py        # Protocol Connector + ConnectorResult
│           ├── architect.py   # ArchitectConnector (reports, audit, config)
│           └── vigil.py       # VigilConnector (SARIF, SBOM)
└── tests/
    ├── conftest.py             # Fixtures compartidos
    ├── test_cli.py             # Tests de CLI (24)
    ├── test_qa_edge_cases.py   # Tests QA Phase 1 (61)
    ├── test_connectors/
    │   ├── test_architect.py       # Tests architect connector (22)
    │   ├── test_vigil.py           # Tests vigil connector (22)
    │   ├── test_qa_edge_cases.py   # Tests QA Phase 7 (20)
    │   └── fixtures/               # SARIF, JSON, YAML, JSONL fixtures
    ├── test_integration/
    │   └── test_full_flow.py       # Tests E2E (10)
    ├── test_config/
    │   ├── test_schema.py      # Tests de schema (7)
    │   └── test_loader.py      # Tests de loader (9)
    ├── test_core/
    │   ├── test_project.py     # Tests de detección (12)
    │   └── test_evidence.py    # Tests de evidencia (20)
    ├── test_provenance/
    │   ├── test_heuristics.py      # Tests heurísticas (23)
    │   ├── test_git_analyzer.py    # Tests git analyzer (15)
    │   ├── test_store.py           # Tests store JSONL (15)
    │   ├── test_attestation.py     # Tests attestation (13)
    │   ├── test_tracker.py         # Tests tracker (7)
    │   ├── test_session_reader.py  # Tests session reader (13)
    │   ├── test_qa_edge_cases.py   # Tests QA Phase 2 (81)
    │   └── fixtures/               # Datos de test
    ├── test_changelog/
    │   ├── test_watcher.py         # Tests watcher (12)
    │   ├── test_differ.py          # Tests differ (19)
    │   ├── test_classifier.py      # Tests classifier (22)
    │   ├── test_renderer.py        # Tests renderer (10)
    │   ├── test_integration.py     # Tests integración (3)
    │   ├── test_qa_edge_cases.py   # Tests QA Phase 3 (27)
    │   └── fixtures/               # Datos de test
    └── test_frameworks/
        ├── test_eu_ai_act/
        │   ├── test_evaluator.py       # Tests evaluador (32)
        │   ├── test_fria.py            # Tests FRIA (23)
        │   ├── test_annex_iv.py        # Tests Annex IV (17)
        │   ├── test_requirements.py    # Tests requirements (9)
        │   └── test_qa_edge_cases.py   # Tests QA Phase 4 (43)
        └── test_owasp/
            ├── test_evaluator.py       # Tests evaluador OWASP (40)
            ├── test_requirements.py    # Tests requirements OWASP (15)
            └── test_qa_edge_cases.py   # Tests QA Phase 5 (48)
    └── test_reports/
        ├── test_unified.py            # Tests unified report (12)
        ├── test_gap_analyzer.py       # Tests gap analyzer (15)
        ├── test_markdown.py           # Tests Markdown renderer (10)
        ├── test_json_fmt.py           # Tests JSON renderer (10)
        ├── test_html.py               # Tests HTML renderer (12)
        ├── test_summary.py            # Tests terminal summary (11)
        └── test_qa_edge_cases.py      # Tests QA Phase 6 (26)
```
