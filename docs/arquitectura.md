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
├── frameworks/      Evaluadores regulatorios (Fase 4 COMPLETADA, 5 pendiente)
│   ├── base.py          Protocol ComplianceFramework
│   ├── registry.py      Registro de frameworks
│   ├── eu_ai_act/   EU AI Act (Fase 4 — COMPLETADA)
│   └── owasp_agentic/  OWASP Agentic Top 10 (Fase 5)
├── connectors/      Integraciones opcionales (Fase 7)
└── reports/         Generación de reportes (Fase 6)
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

4. **Lazy imports**: Los comandos de fases futuras usan imports lazy con `try/except ImportError` para que el CLI funcione sin los módulos aún no implementados.

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

## Módulos implementados (Fases 1-4)

### config/ — Configuración

- **`schema.py`**: 9 modelos Pydantic v2 con clase raíz `LicitConfig`. Todos los campos tienen defaults sensatos.
- **`loader.py`**: Carga configuración con resolución en 3 niveles: path explícito → `.licit.yaml` en cwd → defaults.
- **`defaults.py`**: Constantes: `CONFIG_FILENAME`, `DATA_DIR`, instancia `DEFAULTS`.

### core/ — Núcleo

- **`models.py`**: 3 enums (`ComplianceStatus`, `ChangeSeverity`, `ProvenanceSource`) y 6 dataclasses (`ProvenanceRecord`, `ConfigChange`, `ControlRequirement`, `ControlResult`, `ComplianceSummary`, `GapItem`).
- **`project.py`**: `ProjectDetector` con 8 métodos de detección. Produce un `ProjectContext` completo.
- **`evidence.py`**: `EvidenceCollector` con 5 métodos de recopilación. Produce un `EvidenceBundle` con 18 campos.

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

### cli.py — Interfaz de línea de comandos

10 comandos registrados con Click. Ocho funcionales: `init`, `status`, `connect`, `trace`, `changelog`, `fria`, `annex-iv`, `verify`. Los demás (`report`, `gaps`) tienen firmas completas y help text, pero dependen de módulos de fases futuras.

## Fases de implementación

| Fase | Módulo | Estado | Descripción |
|---|---|---|---|
| 1 | Foundation | **COMPLETADA** | Config, modelos, detección, evidencia, CLI, logging |
| 2 | Provenance | **COMPLETADA** | git_analyzer, heuristics, store JSONL, HMAC, attestation, session readers, report |
| 3 | Changelog | **COMPLETADA** | watcher, differ semántico, classifier (MAJOR/MINOR/PATCH), renderer (MD/JSON) |
| 4 | EU AI Act | **COMPLETADA** | Protocol, registry, evaluador (11 artículos), FRIA interactivo, Annex IV, templates Jinja2 |
| 5 | OWASP | Pendiente | Evaluador OWASP Agentic Top 10 |
| 6 | Reports | Pendiente | Reporte unificado, gap analyzer, Markdown/JSON/HTML |
| 7 | Connectors | Pendiente | Integración con architect y vigil |

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
Phase 5: frameworks/owasp ← core/* + evidence + frameworks/base
Phase 6: reports ← frameworks/* + evidence + core/models
Phase 7: connectors ← config (independiente)
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
│       ├── frameworks/         # Fase 4 (COMPLETADA)
│       │   ├── base.py        # Protocol ComplianceFramework
│       │   ├── registry.py    # FrameworkRegistry
│       │   └── eu_ai_act/     # EU AI Act (Fase 4)
│       │       ├── requirements.py  # 11 requisitos evaluables
│       │       ├── evaluator.py     # Evaluador por artículo
│       │       ├── fria.py          # Generador FRIA interactivo
│       │       ├── annex_iv.py      # Generador Annex IV
│       │       └── templates/       # Jinja2 (FRIA, Annex IV, report section)
│       ├── connectors/         # (Fase 7)
│       └── reports/            # (Fase 6)
└── tests/
    ├── conftest.py             # Fixtures compartidos
    ├── test_cli.py             # Tests de CLI (13)
    ├── test_qa_edge_cases.py   # Tests QA Phase 1 (61)
    ├── test_config/
    │   ├── test_schema.py      # Tests de schema (7)
    │   └── test_loader.py      # Tests de loader (9)
    ├── test_core/
    │   ├── test_project.py     # Tests de detección (12)
    │   └── test_evidence.py    # Tests de evidencia (11)
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
        └── test_eu_ai_act/
            ├── test_evaluator.py       # Tests evaluador (32)
            ├── test_fria.py            # Tests FRIA (23)
            ├── test_annex_iv.py        # Tests Annex IV (17)
            ├── test_requirements.py    # Tests requirements (9)
            └── test_qa_edge_cases.py   # Tests QA Phase 4 (43)
```
