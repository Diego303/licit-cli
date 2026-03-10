# Arquitectura

## Visión general

licit es una herramienta CLI standalone que analiza proyectos de desarrollo asistido por IA para evaluar su compliance regulatorio. Opera de forma local (filesystem-first), sin requerir servicios externos ni bases de datos.

```
licit (CLI)
├── config/          Esquema Pydantic v2 + loader YAML
├── core/            Modelos de dominio + detección + evidencia
├── logging/         structlog configuración
├── provenance/      Trazabilidad de código (Fase 2)
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
       ▼
┌─────────────────┐
│ ProjectDetector  │ ← Detecta lenguajes, frameworks, CI/CD, agentes
└────────┬────────┘
         │ ProjectContext
         ▼
┌─────────────────┐
│EvidenceCollector │ ← Recopila evidencia de .licit/, configs, SARIF
└────────┬────────┘
         │ EvidenceBundle
         ▼
┌─────────────────┐
│   Evaluadores   │ ← EU AI Act, OWASP (Fases 4-5)
└────────┬────────┘
         │ ControlResult[]
         ▼
┌─────────────────┐
│   Reportes      │ ← Markdown, JSON, HTML (Fase 6)
└─────────────────┘
```

## Módulos implementados (Fase 1)

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

### cli.py — Interfaz de línea de comandos

10 comandos registrados con Click. Tres funcionales: `init`, `status`, `connect`. Los demás tienen firmas completas y help text, pero sus imports son lazy para módulos de fases futuras.

## Fases de implementación

| Fase | Módulo | Estado | Descripción |
|---|---|---|---|
| 1 | Foundation | **COMPLETADA** | Config, modelos, detección, evidencia, CLI, logging |
| 2 | Provenance | Pendiente | git_analyzer, heuristics, store JSONL, HMAC, attestation |
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

Phase 2: provenance ← core/models + config
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
│       ├── provenance/         # (Fase 2)
│       ├── changelog/          # (Fase 3)
│       ├── frameworks/         # (Fases 4-5)
│       ├── connectors/         # (Fase 7)
│       └── reports/            # (Fase 6)
└── tests/
    ├── conftest.py             # Fixtures compartidos
    ├── test_cli.py             # Tests de CLI (13)
    ├── test_config/
    │   ├── test_schema.py      # Tests de schema (7)
    │   └── test_loader.py      # Tests de loader (9)
    └── test_core/
        ├── test_project.py     # Tests de detección (12)
        └── test_evidence.py    # Tests de evidencia (11)
```
