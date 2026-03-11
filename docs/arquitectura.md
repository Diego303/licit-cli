# Arquitectura

## Visión general

licit es una herramienta CLI standalone que analiza proyectos de desarrollo asistido por IA para evaluar su compliance regulatorio. Opera de forma local (filesystem-first), sin requerir servicios externos ni bases de datos.

```
licit (CLI)
├── config/          Esquema Pydantic v2 + loader YAML
├── core/            Modelos de dominio + detección + evidencia
├── logging/         structlog configuración
├── provenance/      Trazabilidad de código (Fase 2 — COMPLETADA)
├── changelog/       Registro de cambios en configs de agentes (Fase 3)
├── frameworks/      Evaluadores regulatorios (Fases 4-5)
│   ├── eu_ai_act/   EU AI Act
│   └── owasp_agentic/  OWASP Agentic Top 10
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
       ├──────────────────────────────────────┐
       ▼                                      ▼
┌─────────────────┐                  ┌──────────────────┐
│ ProjectDetector  │                  │ProvenanceTracker  │
│                  │                  │                    │
│ Detecta lenguajes│                  │ ┌──────────────┐  │
│ frameworks, CI/CD│                  │ │ GitAnalyzer   │  │ ← git log
│ agentes          │                  │ │  + Heuristics │  │
└────────┬────────┘                  │ └──────┬───────┘  │
         │ ProjectContext             │        │          │
         ▼                           │ ┌──────────────┐  │
┌─────────────────┐                  │ │SessionReaders │  │ ← ~/.claude/
│EvidenceCollector │                  │ └──────┬───────┘  │
│                  │                  │        │          │
│ .licit/, configs │                  │ ┌──────────────┐  │
│ SARIF, architect │                  │ │  Attestor    │  │ ← HMAC sign
└────────┬────────┘                  │ └──────┬───────┘  │
         │ EvidenceBundle             │        │          │
         ▼                           │ ┌──────────────┐  │
┌─────────────────┐                  │ │    Store     │  │ → provenance.jsonl
│   Evaluadores   │ ← Fases 4-5     │ └──────────────┘  │
└────────┬────────┘                  └──────────┬───────┘
         │ ControlResult[]                      │
         ▼                                      ▼
┌─────────────────┐                  ┌──────────────────┐
│   Reportes      │ ← Fase 6        │ Provenance Report │
└─────────────────┘                  └──────────────────┘
```

## Módulos implementados (Fases 1-2)

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

### cli.py — Interfaz de línea de comandos

10 comandos registrados con Click. Cuatro funcionales: `init`, `status`, `connect`, `trace`. Los demás tienen firmas completas y help text, pero sus imports son lazy para módulos de fases futuras.

## Fases de implementación

| Fase | Módulo | Estado | Descripción |
|---|---|---|---|
| 1 | Foundation | **COMPLETADA** | Config, modelos, detección, evidencia, CLI, logging |
| 2 | Provenance | **COMPLETADA** | git_analyzer, heuristics, store JSONL, HMAC, attestation, session readers, report |
| 3 | Changelog | Pendiente | Watcher de configs de agentes, differ, clasificador |
| 4 | EU AI Act | Pendiente | Evaluador, FRIA interactivo, Annex IV |
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
Phase 3: changelog ← core/models + config
Phase 4: frameworks/eu_ai_act ← core/* + evidence
Phase 5: frameworks/owasp ← core/* + evidence
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
│       ├── changelog/          # (Fase 3)
│       ├── frameworks/         # (Fases 4-5)
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
    └── test_provenance/
        ├── test_heuristics.py      # Tests heurísticas (23)
        ├── test_git_analyzer.py    # Tests git analyzer (15)
        ├── test_store.py           # Tests store JSONL (15)
        ├── test_attestation.py     # Tests attestation (13)
        ├── test_tracker.py         # Tests tracker (7)
        ├── test_session_reader.py  # Tests session reader (13)
        ├── test_qa_edge_cases.py   # Tests QA Phase 2 (81)
        └── fixtures/               # Datos de test
```
