# Seguimiento de Implementación — licit V0

> Documento de seguimiento detallado de la implementación del MVP.
> Actualizado conforme se completan las fases.

---

## Estado General

| Fase | Nombre | Estado | Tests | Archivos |
|------|--------|--------|-------|----------|
| **Phase 1** | Foundation | **COMPLETADA + QA** | 113/113 | 22 source + 8 test |
| Phase 2 | Provenance | Pendiente | — | — |
| Phase 3 | Changelog | Pendiente | — | — |
| Phase 4 | EU AI Act | Pendiente | — | — |
| Phase 5 | OWASP Agentic | Pendiente | — | — |
| Phase 6 | Reports + Gap Analyzer | Pendiente | — | — |
| Phase 7 | Connectors + Integration | Pendiente | — | — |

**Verificación de calidad:**
- `ruff check src/licit/` — Sin errores
- `mypy src/licit/ --strict` — Sin errores (0 issues en 21 archivos)
- `pytest tests/ -q` — 113 tests, todos pasan (52 originales + 61 QA)

---

## Phase 1 — Foundation (COMPLETADA)

### Objetivo
Establecer la base del proyecto: estructura de directorios, sistema de configuración,
modelos de datos core, auto-detección de proyecto, recolección de evidencia, esqueleto
completo del CLI con los 10 comandos, y sistema de logging.

### Módulos Implementados

#### P1.1 — Estructura del proyecto + pyproject.toml

**Archivo:** `pyproject.toml`

Se configuró el proyecto completo con hatchling como build system:
- Nombre del paquete: `licit-ai-cli`
- Versión: `0.1.0`
- Python: `>=3.12`
- 6 dependencias runtime: click, pydantic, structlog, pyyaml, jinja2, cryptography
- 4 dependencias dev: pytest, pytest-cov, ruff, mypy
- Entry point CLI: `licit = "licit.cli:main"`
- Configuración de ruff (line-length=100, target py312), mypy (strict), pytest (testpaths)

**Estructura de directorios creada:** Se estableció toda la estructura del proyecto
según la sección 2 del plan, incluyendo directorios vacíos con `__init__.py` para
módulos de fases futuras (provenance, changelog, frameworks, connectors, reports).
Esto permite que las importaciones lazy del CLI registren los comandos sin error
hasta que los módulos se implementen.

**Archivo:** `src/licit/py.typed` — Marcador PEP 561 para que mypy reconozca el
paquete como tipado.

#### P1.2 — Config schema (Pydantic v2) + loader + defaults

**Archivos:**
- `src/licit/config/schema.py` — 9 modelos Pydantic v2
- `src/licit/config/loader.py` — Carga YAML con fallback a defaults
- `src/licit/config/defaults.py` — Constantes por defecto

**Modelos de configuración (`schema.py`):**

| Modelo | Campos principales | Propósito |
|--------|-------------------|-----------|
| `LicitConfig` | Raíz con 7 sub-configs | Configuración principal |
| `ProvenanceConfig` | enabled, methods, confidence_threshold, sign, store_path | Control del tracking de provenance |
| `ChangelogConfig` | enabled, watch_files (8 patrones), output_path | Monitoreo de configs de agentes |
| `FrameworkConfig` | eu_ai_act, owasp_agentic, nist_ai_rmf, iso_42001 | Frameworks habilitados |
| `ConnectorsConfig` | architect, vigil (sub-configs) | Conectores opcionales |
| `ConnectorArchitectConfig` | enabled, reports_dir, audit_log, config_path | Conector architect |
| `ConnectorVigilConfig` | enabled, sarif_path, sbom_path | Conector vigil |
| `FRIAConfig` | output_path, data_path, organization, system_name | Generador FRIA |
| `AnnexIVConfig` | output_path, organization, product_name, product_version | Documentación Annex IV |
| `ReportConfig` | output_dir, default_format, include_evidence, include_recommendations | Formato de reportes |

**Loader (`loader.py`):**
- Resolución de config en 3 niveles: path explícito → `.licit.yaml` en cwd → defaults
- Manejo robusto de errores: YAML inválido, archivo inexistente, datos no-dict
- Función `save_config()` para persistir configuración (usada por `init` y `connect`)
- Todo con logging structlog para trazabilidad

**Defaults (`defaults.py`):**
- Instancia canónica `DEFAULTS = LicitConfig()`
- Constantes: `CONFIG_FILENAME = ".licit.yaml"`, `DATA_DIR = ".licit"`

#### P1.3 — Core models (dataclasses)

**Archivo:** `src/licit/core/models.py`

3 enumeraciones + 6 dataclasses que forman el modelo de datos central:

**Enumeraciones (usando `StrEnum` para compatibilidad con serialización JSON):**
- `ComplianceStatus` — 5 estados: compliant, partial, non-compliant, n/a, not-evaluated
- `ChangeSeverity` — 3 niveles: major, minor, patch
- `ProvenanceSource` — 5 métodos: git-infer, session-log, git-ai, manual, connector

**Dataclasses:**
- `ProvenanceRecord` — Registro de provenance de un archivo (12 campos: file_path, source, confidence, method, timestamp, lines_range, model, agent_tool, session_id, spec_ref, cost_usd, signature)
- `ConfigChange` — Cambio detectado en config de agente (8 campos)
- `ControlRequirement` — Requisito de compliance de un framework (6 campos)
- `ControlResult` — Resultado de evaluar un control (7 campos con defaults)
- `ComplianceSummary` — Estadísticas agregadas de evaluación (8 campos)
- `GapItem` — Gap de compliance con recomendación accionable (7 campos)

**Decisión de diseño:** Se usó `StrEnum` en lugar de `(str, Enum)` del plan original.
Ruff UP042 requiere esto para Python 3.12+. Es funcionalmente equivalente pero más
idiomático.

#### P1.4 — ProjectDetector (auto-detección)

**Archivo:** `src/licit/core/project.py`

4 dataclasses de soporte + 1 clase principal:

**Dataclasses:**
- `AgentConfigFile` — Archivo de config de agente detectado (path, agent_type, exists)
- `CICDConfig` — Plataforma CI/CD detectada (platform, config_path, has_ai_steps)
- `SecurityTooling` — Herramientas de seguridad (8 flags booleanos + sarif_files)
- `ProjectContext` — Contexto completo del proyecto (20+ campos organizados en categorías)

**`ProjectDetector` — 8 métodos de detección:**

| Método | Qué detecta | Fuentes |
|--------|-------------|---------|
| `_detect_name` | Nombre del proyecto | pyproject.toml, package.json |
| `_detect_languages` | Lenguajes + package managers | pyproject.toml, package.json, go.mod, Cargo.toml, pom.xml, build.gradle |
| `_detect_frameworks` | Frameworks web/app | Contenido de pyproject.toml, requirements.txt, package.json |
| `_detect_agent_configs` | Configs de agentes AI | 10 patrones: CLAUDE.md, .cursorrules, AGENTS.md, .github/copilot-instructions.md, architect configs, etc. |
| `_detect_cicd` | Plataforma CI/CD | 5 patrones: GitHub Actions, GitLab CI, Jenkins, CircleCI |
| `_detect_testing` | Framework de tests | Directorios tests/test/__tests__ + package.json (jest/vitest) |
| `_detect_security` | Herramientas de seguridad | .vigil.yaml, .semgrep.yml, .snyk, .github/codeql, archivos .sarif |
| `_detect_git` | Info de git | git rev-parse, rev-list, shortlog |

**Manejo de errores:** Cada método de detección captura excepciones específicas
(JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError) y las registra con
structlog sin interrumpir el flujo.

#### P1.5 — EvidenceCollector

**Archivo:** `src/licit/core/evidence.py`

**`EvidenceBundle` — 18 campos de evidencia organizados en categorías:**
- Provenance: has_provenance, provenance_stats
- Changelog: has_changelog, changelog_entry_count
- FRIA/Annex IV: has_fria, fria_path, has_annex_iv, annex_iv_path
- Guardrails: has_guardrails, guardrail_count, has_quality_gates, quality_gate_count
- Audit: has_audit_trail, audit_entry_count, has_otel
- Oversight: has_human_review_gate, has_dry_run, has_rollback
- Security: security_findings_total, security_findings_critical, security_findings_high

**`EvidenceCollector` — 5 métodos de recolección:**

| Método | Fuente | Evidencia recolectada |
|--------|--------|----------------------|
| `_collect_licit_data` | `.licit/` directory | provenance.jsonl, changelog.md, fria-data.json, annex-iv.md |
| `_collect_project_evidence` | Configs del proyecto | architect guardrails, quality gates, budget limits |
| `_parse_architect_config` | `.architect/config.yaml` | Guardrail count, quality gate count, budget, dry-run, rollback |
| `_collect_architect_evidence` | `.architect/reports/` | Audit trail (count de JSON reports) |
| `_collect_vigil_evidence` | Archivos `.sarif` | Security findings por severidad (critical, high, total) |

**Decisión de diseño:** La importación de `ProvenanceStore` (Phase 2) se hace con
`try/except ImportError` para que el EvidenceCollector funcione sin el módulo de
provenance instalado. Esto permite que Phase 1 sea completamente funcional.

#### P1.6 — CLI skeleton (10 comandos)

**Archivo:** `src/licit/cli.py`

10 comandos Click registrados con firmas completas, help text, y opciones tipadas:

| Comando | Opciones | Estado en Phase 1 |
|---------|----------|-------------------|
| `init` | `--framework [eu-ai-act\|owasp\|all]` | **Funcional** — Detecta proyecto, crea `.licit.yaml` y `.licit/` |
| `trace` | `--since`, `--report`, `--stats` | Esqueleto — Depende de Phase 2 (provenance) |
| `changelog` | `--since`, `--format [markdown\|json]` | Esqueleto — Depende de Phase 3 |
| `fria` | `--update` | Esqueleto — Depende de Phase 4 |
| `annex-iv` | `--organization`, `--product` | Esqueleto — Depende de Phase 4 |
| `report` | `--framework`, `--format`, `--output` | Esqueleto — Depende de Phase 6 |
| `gaps` | `--framework` | Esqueleto — Depende de Phase 6 |
| `verify` | `--framework` | Esqueleto — Depende de Phase 4-6 |
| `status` | (ninguna) | **Funcional** — Muestra estado completo |
| `connect` | `CONNECTOR [architect\|vigil]`, `--enable/--disable` | **Funcional** — Modifica `.licit.yaml` |

**Patrón de lazy imports:** Los comandos que dependen de fases futuras usan imports
dentro del cuerpo de la función. Esto permite que `--help` funcione para todos los
comandos, y los que son funcionales (init, status, connect) operan completamente.
Los demás fallarán con ImportError al ejecutarse hasta que se implementen sus módulos.

**Tipado:** Se usa `Any` para tipos de retorno de módulos futuros, con
`# type: ignore[import-not-found]` en los imports lazy. Esto mantiene mypy --strict
limpio mientras permite desarrollo incremental.

#### P1.7 — Logging setup + tests

**Archivo:** `src/licit/logging/setup.py`

Configuración de structlog con:
- Nivel WARNING por defecto (no verbose), DEBUG con `-v`
- `WriteLoggerFactory()` — Compatible con Click's CliRunner (evita errores de stderr cerrado)
- `cache_logger_on_first_use=False` — Permite reconfigurar entre tests
- Procesadores: contextvars, log level, stack info, exc info, timestamps, ConsoleRenderer

### Tests (113 total)

| Archivo | # Tests | Qué cubre |
|---------|---------|-----------|
| `tests/test_cli.py` | 13 | Help de todos los comandos, init crea config y directorio, init con --framework, status sin init, connect enable/disable |
| `tests/test_config/test_schema.py` | 7 | Defaults de todas las secciones, roundtrip model_dump/validate, config parcial con defaults |
| `tests/test_config/test_loader.py` | 9 | Load sin archivo, load explícito, load desde cwd, YAML inválido, path inexistente, save y roundtrip |
| `tests/test_core/test_project.py` | 12 | Detección Python/JS/Go, agent configs, architect, CI/CD, security tools, git info, proyecto vacío |
| `tests/test_core/test_evidence.py` | 11 | Bundle vacío, FRIA/Annex IV/changelog, GitHub Actions → review gate, architect guardrails, SARIF parsing |
| `tests/test_qa_edge_cases.py` | 61 | **QA hardening** — ver sección de QA más abajo |
| `tests/conftest.py` | — | Fixtures: `tmp_project`, `git_project`, `make_context()`, `make_evidence()` + structlog CRITICAL |

### Decisiones Técnicas

1. **Nombre del paquete** cambió de `licit-ai` a `licit-ai-cli` por un hook de pre-commit del proyecto.

2. **`LicitConfig`** en lugar de `ComplyConfig` del plan — Más coherente con el nombre del proyecto y evita confusión con el nombre anterior del proyecto.

3. **structlog con `WriteLoggerFactory`** en lugar de `PrintLoggerFactory(file=sys.stderr)` — El CliRunner de Click captura/cierra stderr durante tests, causando `ValueError: I/O operation on closed file`. WriteLoggerFactory escribe a stdout por defecto y es más robusto.

4. **Tests suprimen structlog a CRITICAL** en conftest.py — Evita ruido en la salida de tests sin requerir mocks complejos.

### QA Hardening (post-implementación)

Se realizó una revisión de QA completa sobre toda la Phase 1: verificación estática
(`ruff --select ALL`, `mypy --strict`), análisis de código, revisión de tests, y
escritura de tests adicionales de edge cases.

#### Bugs encontrados y corregidos

| # | Severidad | Archivo | Problema | Corrección |
|---|-----------|---------|----------|------------|
| 1 | **Alta** | `config/schema.py` | `confidence_threshold` aceptaba cualquier float (ej: 5.0, -1.0) | Añadido `ge=0.0, le=1.0` en el `Field()` de Pydantic |
| 2 | **Media** | `core/project.py` | `_detect_git` solo capturaba `FileNotFoundError`, no `PermissionError` | Cambiado a `except (TimeoutExpired, OSError)` — OSError cubre ambos |
| 3 | **Media** | `core/evidence.py` | `_parse_architect_config` usaba `except Exception` genérico | Narrowed a `(YAMLError, OSError, KeyError, TypeError, ValueError)` |
| 4 | **Media** | `core/evidence.py` | `has_dry_run` y `has_rollback` se ponían `True` incondicionalmente cuando existía architect config | Ahora condicional: solo `True` si no están explícitamente deshabilitados en el config |
| 5 | **Baja** | `core/project.py` | Si existían `pyproject.toml` y `package.json`, el nombre de `package.json` sobreescribía al de `pyproject.toml` | `package.json` solo se usa para nombre si `pyproject.toml` no existe |
| 6 | **Baja** | `core/evidence.py` | `.count("##")` contaba headers `###`, `####` como entradas de changelog | Cambiado a contar solo líneas que empiezan con `"## "` |

#### Tests de QA añadidos (61 nuevos)

**Archivo:** `tests/test_qa_edge_cases.py`

| Clase | # Tests | Cobertura |
|-------|---------|-----------|
| `TestConfigValidation` | 10 | Threshold fuera de rango, boundary 0/1, campos extra ignorados, YAML vacío, null, unicode, roundtrip unicode, threshold inválido en YAML |
| `TestCoreModels` | 11 | Valores de enums, membership, enum inválido, ProvenanceRecord mínimo y completo, ControlResult defaults, GapItem defaults, ComplianceSummary, ConfigChange |
| `TestProjectDetectorEdgeCases` | 14 | Prioridad pyproject>package.json, Rust, Java Maven/Gradle, pyproject malformado, package.json malformado, múltiples CI/CD, pyproject sin [project], package.json sin name, SARIF, CodeQL, Snyk, Copilot, múltiples agentes |
| `TestEvidenceCollectorEdgeCases` | 12 | provenance.jsonl sin módulo, architect config malformado, config no-dict, guardrails vacíos, SARIF non-vigil ignorado, SARIF malformado, SARIF inexistente, h3 no contados, directorio .licit vacío, dry_run/rollback defaults, dry_run explícitamente false |
| `TestCLIEdgeCases` | 7 | Connect persiste en YAML, disable persiste, status con config, init→status integración, framework inválido, help de todos los comandos, flag verbose |
| `TestImportSafety` | 8 | Import de cada módulo sin circular imports, versión existe |

#### Documentación técnica

Se creó la carpeta `docs/` con 10 documentos en español:

| Documento | Contenido |
|-----------|-----------|
| `docs/README.md` | Índice principal |
| `docs/inicio-rapido.md` | Guía de 5 minutos |
| `docs/arquitectura.md` | Stack, flujo de datos, módulos, fases, dependencias |
| `docs/guia-cli.md` | Los 10 comandos con opciones y ejemplos |
| `docs/configuracion.md` | Todos los campos de `.licit.yaml` |
| `docs/modelos.md` | Enums, dataclasses, EvidenceBundle, jerarquía Pydantic |
| `docs/seguridad.md` | Modelo de amenazas, HMAC, parsing seguro |
| `docs/compliance.md` | EU AI Act (9 artículos), OWASP (10 riesgos), CI/CD gate |
| `docs/buenas-practicas.md` | 18 recomendaciones + antipatrones |
| `docs/desarrollo.md` | Setup, convenciones, testing, flujo de contribución |
| `docs/faq.md` | Instalación, problemas conocidos, glosario |

#### Riesgos residuales identificados

| Riesgo | Impacto | Nota |
|--------|---------|------|
| `rglob("*.sarif")` puede ser lento en proyectos con `node_modules` | Bajo | Considerar excluir dirs en futuras fases |
| CLI tests usan `os.chdir()` (no thread-safe) | Bajo | OK para ejecución secuencial; migrar si se usa `pytest-xdist` |
| `has_human_review_gate = True` asume que GitHub Actions = PR reviews | Bajo | Refinar en Phase 4 con análisis real de workflow |

---

## Phase 2 — Provenance (PENDIENTE)

Módulos a implementar:
- `src/licit/provenance/git_analyzer.py`
- `src/licit/provenance/heuristics.py`
- `src/licit/provenance/store.py`
- `src/licit/provenance/tracker.py`
- `src/licit/provenance/attestation.py`
- `src/licit/provenance/session_readers/base.py`
- `src/licit/provenance/session_readers/claude_code.py`
- `src/licit/provenance/report.py`

---

## Phase 3 — Changelog (PENDIENTE)

Módulos a implementar:
- `src/licit/changelog/watcher.py`
- `src/licit/changelog/differ.py`
- `src/licit/changelog/classifier.py`
- `src/licit/changelog/renderer.py`

---

## Phase 4 — EU AI Act (PENDIENTE)

Módulos a implementar:
- `src/licit/frameworks/base.py`
- `src/licit/frameworks/registry.py`
- `src/licit/frameworks/eu_ai_act/requirements.py`
- `src/licit/frameworks/eu_ai_act/evaluator.py`
- `src/licit/frameworks/eu_ai_act/fria.py`
- `src/licit/frameworks/eu_ai_act/annex_iv.py`
- Templates Jinja2

---

## Phase 5 — OWASP Agentic (PENDIENTE)

## Phase 6 — Reports + Gap Analyzer (PENDIENTE)

## Phase 7 — Connectors + Integration (PENDIENTE)
