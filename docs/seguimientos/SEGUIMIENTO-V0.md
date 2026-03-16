# Seguimiento de Implementación — licit V0

> Documento de seguimiento detallado de la implementación del MVP.
> Actualizado conforme se completan las fases.

---

## Estado General

| Fase | Nombre | Estado | Tests | Archivos |
|------|--------|--------|-------|----------|
| **Phase 1** | Foundation | **COMPLETADA + QA** | 113/113 | 22 source + 8 test |
| **Phase 2** | Provenance | **COMPLETADA + QA** | 167/167 | 10 source + 7 test |
| **Phase 3** | Changelog | **COMPLETADA + QA** | 93/93 | 5 source + 11 test |
| **Phase 4** | EU AI Act | **COMPLETADA + QA** | 124/124 | 9 source + 3 templates + 5 test |
| **Phase 5** | OWASP Agentic | **COMPLETADA + QA** | 103/103 | 3 source + 1 template + 3 test |
| **Phase 6** | Reports + Gap Analyzer | **COMPLETADA + QA** | 106/106 | 6 source + 7 test |
| **Phase 7** | Connectors + Integration | **COMPLETADA + QA** | 83/83 | 4 source + 6 fixtures + 4 test |
| **QA V0** | Test Exhaustivo + Bug Fixes | **COMPLETADA** | 789/789 | 5 source modificados + 3 test |

**Verificación de calidad (v1.0.0):**
- `ruff check src/licit/` — Sin errores
- `mypy src/licit/ --strict` — Sin errores (0 issues en 50 archivos)
- `pytest tests/ -q` — 789 tests, todos pasan
- QA exhaustivo: 142 tests manuales × 5 proyectos simulados × 10 edge cases → 0 bugs pendientes

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
- Versión: `0.6.0`
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

## Phase 2 — Provenance (COMPLETADA)

### Objetivo
Implementar el sistema completo de tracking de provenance: análisis heurístico de
git history, lectores de sesiones de agentes AI, store JSONL append-only, attestation
criptográfica con HMAC-SHA256, generación de reportes, y orquestación vía tracker.

### Módulos Implementados

#### P2.1 — Heuristics Engine

**Archivo:** `src/licit/provenance/heuristics.py`

Motor de 6 heurísticas para detectar commits AI-generados. Cada heurística produce
un score (0-1) con peso (weight). El score final es un promedio ponderado de solo
las heurísticas que producen señal (score > 0), evitando que heurísticas silenciosas
diluyan señales fuertes.

| Heurística | Peso | Qué detecta |
|------------|------|-------------|
| H1: Author pattern | 3.0 | Nombres de autor conocidos (claude, copilot, cursor, devin, bot, etc.) |
| H2: Message pattern | 1.5 | Patrones de commit message (conventional commits, "implement", "generated by", `[ai]`, `[bot]`) |
| H3: Bulk changes | 2.0 | Cambios masivos (>20 files + >500 lines = 0.6, >10 files + >200 lines = 0.3) |
| H4: Co-authors | 3.0 | Co-authored-by con keywords AI (claude, copilot, ai, bot, anthropic) |
| H5: File patterns | 1.0 | Todos los archivos son test files (test_*.py, *.spec.ts, etc.) |
| H6: Time patterns | 0.5 | Commits entre 1am-5am |

**Extensibilidad:** Soporta custom patterns desde archivo JSON (`ai_authors` + `message_patterns`).
Regex inválidos en patterns custom se capturan con `try/except re.error` sin crashear.

#### P2.2 — Git Analyzer

**Archivo:** `src/licit/provenance/git_analyzer.py`

Analiza git history usando `git log --format=... --numstat`. Parsea la salida con
separadores `\x00` (record) y `\x01` (field) para robustez — evita conflictos con
pipes, comillas, o caracteres especiales en mensajes de commit.

**Dataclass:** `CommitInfo` con 9 campos (sha, author, author_email, date, message,
files_changed, insertions, deletions, co_authors).

**Funcionalidades:**
- Parsing robusto de numstat con `split("\t", 2)` para manejar tabs en filenames
- Extracción case-insensitive de co-authors vía regex `re.IGNORECASE`
- Inferencia de agente (8 patrones: claude→claude-code, cursor→cursor, etc.)
- Inferencia de modelo (8 regex: claude-opus-4, claude-sonnet-4, gpt-4.1, gemini, etc.)
- Clasificación: score >= 0.7 → "ai", score >= 0.5 → "mixed", score < 0.5 → "human"
- Timeout de 30 segundos para `subprocess.run`
- Formato git: usa `%x00`/`%x01` (hex escapes) en lugar de null bytes literales en CLI args

#### P2.3 — Provenance Store (JSONL)

**Archivo:** `src/licit/provenance/store.py`

Store append-only en formato JSONL. Cada línea es un `ProvenanceRecord` serializado.

**Operaciones:**
- `append(records)` — Escribe records como JSON lines. Maneja serialización de datetime (ISO format), lines_range (tuple→list), y campos opcionales.
- `load_all()` — Lee y deserializa todos los records. Restaura tipos (datetime, ProvenanceSource enum, lines_range list→tuple). Líneas corruptas se logean y se saltan.
- `get_stats()` — Estadísticas con deduplicación por archivo (último timestamp gana). Calcula ai_percentage: `(ai + mixed*0.5) / total * 100`.
- `get_by_file(path)` — Todos los records de un archivo específico.

**Robustez:** Crea directorios padre automáticamente. Maneja JSON/key/value/type errors en carga con logging debug.

#### P2.4 — Cryptographic Attestation

**Archivo:** `src/licit/provenance/attestation.py`

Firma HMAC-SHA256 para integridad de records con Merkle tree para firma batch.

**Operaciones:**
- `sign_record(data)` — HMAC-SHA256 sobre JSON canónico (sorted keys, default=str). Retorna hex digest de 64 chars.
- `verify_record(data, signature)` — Verificación con `hmac.compare_digest` (timing-safe).
- `sign_batch(records)` — Merkle tree: SHA256 por record → construir árbol binario → raíz. Elementos impares se duplican.

**Key management:**
1. Path explícito (si proporcionado)
2. Fallback: `.licit/.signing-key` (project-local)
3. Si no existe: genera 32 bytes con `os.urandom(32)` y persiste
4. Todos los accesos a filesystem tienen `try/except OSError`

#### P2.5 — Session Readers (Protocol + Claude Code)

**Archivos:**
- `src/licit/provenance/session_readers/base.py` — Protocol `SessionReader` con `agent_name` property y `read_sessions()` method
- `src/licit/provenance/session_readers/claude_code.py` — Implementación para Claude Code

**ClaudeCodeSessionReader:**
- Lee archivos JSONL de `~/.claude/projects/` o directorios configurados
- Extrae provenance de entries `tool_use` con tool `Write` o `Edit`
- Maneja `params: null` (Bug #2 corregido), `tool` no-string, `file_path` vacío/no-string
- Bash commands con `>`, `tee`, `cp` se saltan (no se puede determinar archivo)
- Timestamp fallback a `datetime.now()` con warning log si inválido
- Model extraído solo si es string

#### P2.6 — Provenance Report

**Archivo:** `src/licit/provenance/report.py`

Genera reportes Markdown con:
- Summary table (total files, AI/human/mixed counts y porcentajes)
- AI Tools Detected (tabla con conteo por agente)
- Models Detected (tabla con conteo por modelo)
- File Details (tabla con path, source, confidence, method, agent)
- Deduplicación: último timestamp por archivo gana
- Pipes en file paths escapados con `\|`
- Crea directorios padre automáticamente

#### P2.7 — Provenance Tracker (Orchestrator)

**Archivo:** `src/licit/provenance/tracker.py`

Orquesta todo el pipeline de provenance:
1. Git analysis (si method `git-infer` configurado)
2. Session reading (si method `session-log` configurado)
3. Filtrado por `confidence_threshold` (records humanos siempre pasan)
4. Signing con `ProvenanceAttestor` (si `sign=true`)
5. Store en JSONL

**Flujo de ejecución:** Si `enabled=false`, retorna lista vacía sin procesar.

#### P2.8 — CLI Integration

**Archivo:** `src/licit/cli.py` (modificado)

El comando `trace` ahora usa las implementaciones reales:
- Imports directos de `ProvenanceStore`, `ProvenanceTracker`, `generate_provenance_report`
  (sin `# type: ignore[import-not-found]` ni `Any`)
- Pipeline completo: tracker.analyze() → store.get_stats() → report

#### P2.9 — Evidence Integration

**Archivo:** `src/licit/core/evidence.py` (modificado)

- Importación directa de `ProvenanceStore` (sin `try/except ImportError`)
- Fix de guardrail values null: `guardrails.get("protected_files") or []`

### Tests (167 total de provenance)

| Archivo | # Tests | Qué cubre |
|---------|---------|-----------|
| `tests/test_provenance/test_heuristics.py` | 23 | 6 heurísticas, custom patterns, human commits |
| `tests/test_provenance/test_git_analyzer.py` | 15 | Parsing (single/multi/co-authors/binary/pipes), agent/model inference, analysis pipeline |
| `tests/test_provenance/test_store.py` | 15 | Append (creates/writes/additive/empty), Load (all/empty/types/lines_range/corrupt), Stats (empty/counts/dedup/percentage), get_by_file |
| `tests/test_provenance/test_attestation.py` | 13 | Sign/verify (valid/tampered/wrong/deterministic), Merkle (single/multi/deterministic/empty/different), Key management (load/generate/reuse) |
| `tests/test_provenance/test_tracker.py` | 7 | Analysis pipeline, since param, disabled, threshold, signing, session reading, multiple methods |
| `tests/test_provenance/test_session_reader.py` | 13 | Write/Edit tools, non-file skip, non-tool skip, multi files, empty/nonexistent dirs, nested, malformed JSON, invalid timestamp, missing file_path, session_id |
| `tests/test_provenance/test_qa_edge_cases.py` | 81 | **QA hardening** — ver sección de QA |

### Fixtures de test

- `tests/test_provenance/fixtures/git_logs/ai_commits.txt` — Commits AI para testing
- `tests/test_provenance/fixtures/git_logs/human_commits.txt` — Commits humanos para testing
- `tests/test_provenance/fixtures/sessions/claude_session.jsonl` — Sesión Claude Code para testing

### Decisiones Técnicas

1. **Scoring con solo heurísticas señalizantes** — El promedio ponderado solo incluye heurísticas con score > 0. Esto evita que 5 heurísticas silenciosas diluyan una señal fuerte (ej: author "Claude" pasaba de 0.95 → 0.259 → ahora 0.95).

2. **Separadores `\x00`/`\x01` en git log** — Más robusto que `|` o `,` que pueden aparecer en mensajes de commit. Se usan hex escapes de git (`%x00`, `%x01`) en el format string para evitar null bytes literales en argumentos CLI.

3. **Protocol para SessionReader** — Interface basada en Protocol (no ABC) para extensibilidad sin herencia. Nuevos lectores (Cursor, Codex) solo necesitan implementar `agent_name` y `read_sessions()`.

4. **HMAC-SHA256 local** — V0 usa signing local con key en `.licit/.signing-key`. V1 migrará a Sigstore/cosign para firma pública verificable.

5. **Store append-only** — Records nunca se borran, solo se agregan. Deduplicación por timestamp más reciente en queries/stats. Prioriza integridad sobre eficiencia de almacenamiento.

6. **Human records siempre pasan threshold** — Por diseño, records con source="human" nunca se filtran por confidence_threshold. Siempre queremos registrar "no se detectó AI".

### QA Hardening (post-implementación)

Se realizó una revisión de QA completa: verificación estática, análisis profundo de
código, ejecución de tests existentes, escritura de 81 tests de edge cases, y prueba
de integración end-to-end con git repo real.

#### Bugs encontrados y corregidos

| # | Severidad | Archivo | Problema | Corrección |
|---|-----------|---------|----------|------------|
| 1 | **Alta** | `heuristics.py` | `re.search()` crashea con regex inválido de custom patterns | Wrapped en `try/except re.error` con `logger.debug` |
| 2 | **Alta** | `claude_code.py` | `params: null` en JSON causa crash — `entry.get("params", {})` retorna `None` cuando key existe con valor null | Extrae raw_params primero, luego `isinstance(raw_params, dict)` check |
| 3 | **Alta** | `evidence.py` | `len(None)` cuando guardrail values son `null` en YAML — `guardrails.get("protected_files", [])` retorna `None` | Cambiado a `guardrails.get("protected_files") or []` |
| 4 | **Crítica** | `git_analyzer.py` | `ValueError: embedded null byte` — literal `\x00` en argumento de subprocess impide toda ejecución real | Cambiado a `%x00`/`%x01` (hex escapes de git) en format string |
| 5 | **Baja** | `git_analyzer.py` | `split("\t")` sin limit puede cortar filenames con tabs | Cambiado a `split("\t", 2)` |
| 6 | **Baja** | `git_analyzer.py` | Co-author regex no era case-insensitive | Añadido `re.IGNORECASE` |
| 7 | **Baja** | `claude_code.py` | Timestamp inválido caía silenciosamente a `now()` sin warning | Añadido `logger.warning("session_entry_invalid_timestamp", ...)` |
| 8 | **Baja** | `attestation.py` | Key read/write sin manejo de OSError | Añadido `try/except OSError` en read y write de key file |
| 9 | **Baja** | `report.py` | Pipe chars en file paths rompían tabla markdown | Añadido `replace("|", "\\|")` |

**Bug #4 merece mención especial:** Impedía toda ejecución real de `licit trace` en
cualquier repositorio git. Solo era invisible en unit tests porque mockeaban
`subprocess.run`. Descubierto durante el test de integración E2E (Step 5).

#### Tests de QA añadidos (81 nuevos)

**Archivo:** `tests/test_provenance/test_qa_edge_cases.py`

| Clase | # Tests | Cobertura |
|-------|---------|-----------|
| `TestRegressionBug1InvalidRegex` | 2 | Regex inválidos no crashean |
| `TestRegressionBug2NullParams` | 3 | params null/list/string manejados |
| `TestRegressionBug3NullGuardrailValues` | 1 | len(None) prevenido |
| `TestHeuristicsEdgeCases` | 15 | Empty strings, unicode, score cap, all-fire, boundaries (1am/5am/6am/midnight), empty JSON, non-dict JSON |
| `TestGitAnalyzerEdgeCases` | 13 | Unicode paths/authors, tab-in-filename, malformed date, timeout, OSError, no files, multi co-authors, case-insensitive, agent from message, since param |
| `TestStoreEdgeCases` | 12 | Unicode roundtrip, special chars, empty path, None fields, 500 records, all-ai/all-human stats, multi versions, blank lines, deep dirs, signature preserved |
| `TestAttestationEdgeCases` | 9 | Empty/nested/unicode data, different keys, empty sig, large batch, odd Merkle, non-writable dir, datetime serialization |
| `TestSessionReaderEdgeCases` | 10 | Empty/integer file_path, unicode path, non-string tool, non-dict entries, bash redirect, no timestamp, non-string model, multiple dirs |
| `TestReportEdgeCases` | 11 | Empty/single records, pipe escape, unicode, dedup, all sources, no agents/models, multi agents, file creation, parent dirs, sorted files |
| `TestCrossModuleIntegration` | 4 | Git→Store→Report pipeline, store↔report consistency, sign+store+verify, session→store roundtrip |
| `TestTrackerEdgeCases` | 3 | Empty methods, unknown method, threshold=0 |

#### Verificación estática final

| Herramienta | Resultado |
|-------------|-----------|
| `ruff check src/licit/provenance/` | ✅ 0 errores |
| `mypy --strict src/licit/provenance/` | ✅ 0 errores en 10 archivos |
| `pytest tests/` | ✅ 280 tests passed |
| E2E real git repo | ✅ Pipeline completo verificado |

#### Riesgos residuales

| Riesgo | Impacto | Nota |
|--------|---------|------|
| `datetime.now()` sin timezone en session reader | Bajo | Aceptable V0; usar `datetime.now(UTC)` en V1 |
| Store O(n) en `load_all()` para stats/query | Bajo | Aceptable V0; indexar en V1 si necesario |
| Race condition teórica en key generation | Negligible | CLI es single-process |
| `git log --numstat` puede ser lento en repos masivos | Medio | Mitigable con `--since`; timeout de 30s |

---

## Phase 3 — Changelog (COMPLETADA)

### Objetivo
Implementar el sistema de monitoreo de cambios en archivos de configuración de agentes
AI: detección de cambios via git history, diffing semántico por formato, clasificación
de severidad (MAJOR/MINOR/PATCH), y rendering en Markdown/JSON.

### Módulos Implementados

#### P3.1 — Config Watcher

**Archivo:** `src/licit/changelog/watcher.py`

Monitorea archivos de configuración de agentes AI a través del historial de git.

**Dataclass:** `ConfigSnapshot` con 5 campos (path, content, commit_sha, timestamp, author).

**Clase:** `ConfigWatcher` — Recibe `root_dir` y `watch_patterns`. Resuelve patrones
a archivos tracked por git, luego recupera snapshots históricos.

**Métodos:**

| Método | Qué hace |
|--------|----------|
| `get_watched_files()` | Archivos que existen en filesystem (no requiere git) |
| `get_config_history(since?)` | Dict `{file: [ConfigSnapshot, ...]}` newest-first |
| `_resolve_tracked_files()` | Resuelve globs + verifica git history |
| `_file_has_git_history(path)` | `git log --oneline -1` con timeout 10s |
| `_get_file_history(path, since?)` | `git log --format=%H\x01%aI\x01%an --follow` con timeout 30s |
| `_get_file_at_commit(path, sha)` | `git show {sha}:{path}` con size guard |

**Robustez:**
- `_MAX_CONTENT_BYTES = 1_048_576` — Guard contra archivos binarios accidentalmente tracked
- Todos los `subprocess.run` con `timeout=` y `check=False` explícito
- Deduplicación con `seen: set[str]` en resolución de patrones
- Logging structlog en timeout, failure, y archivos oversized

#### P3.2 — Semantic Differ

**Archivo:** `src/licit/changelog/differ.py`

Diffing semántico por formato de archivo. Produce `FieldDiff` en vez de diffs de línea.

**Dataclass:** `FieldDiff` con 5 campos (field_path, old_value, new_value, is_addition, is_removal).

**Dispatch por extensión:**

| Extensión | Estrategia | Función |
|-----------|-----------|---------|
| `.yaml`, `.yml` | Dict recursivo key-value | `_diff_yaml()` |
| `.json` | Dict recursivo key-value | `_diff_json()` |
| `.md` | Secciones por headings | `_diff_markdown()` |
| Otros | Texto completo | `_diff_text()` |

**Funciones auxiliares:**
- `_coerce_to_dict()` — Wraps non-dict roots (listas, escalares) como `{"(root)": data}` en lugar de descartar silenciosamente. Log debug cuando se detecta root no-dict.
- `_diff_dicts()` — Diff recursivo. Dicts anidados se recurren; otros tipos producen FieldDiff directo.
- `_parse_md_sections()` — Parsea markdown en `{heading: body}`. Trackea fenced code blocks (```) para evitar falsos positivos con headings dentro de código.
- `_to_str()` — Convierte valores a string para display; None se mantiene como None.

**Robustez:**
- YAML/JSON parse errors producen `FieldDiff(field_path="(parse-error)")` en vez de crash
- Markdown sin headings cae a diff de texto completo como `(content)`
- Empty strings producen `[]` (no diffs)

#### P3.3 — Change Classifier

**Archivo:** `src/licit/changelog/classifier.py`

Clasifica cambios por severidad usando los FieldDiff del differ.

**Reglas de severidad:**
- **MAJOR:** Cambio en campo de `_MAJOR_FIELDS` (model, provider, backend y variantes con prefijo llm/agent)
- **MINOR:** Cambio en campo de `_MINOR_FIELDS` (prompt, guardrails, rules, tools, etc.) o secciones markdown
- **MAJOR (escalación):** Eliminación de un campo MINOR (ej: borrar `guardrails`)
- **PATCH:** Todo lo demás (tweaks de parámetros, formatting)

**Matching por segmentos (`_field_matches`):**
Compara los últimos N segmentos del field_path contra el patrón. Ejemplo:
- `llm.model` matches `model` ✓ (último segmento coincide)
- `model_config` NO matches `model` ✗ (es un solo segmento diferente)
- `section:model` NO matches `model` ✗ (es un solo segmento "section:model")

Esto previene falsos positivos donde campos como `model_config` o `system_model`
se clasificaban erróneamente como MAJOR.

**Timestamp:** Usa `datetime.now(tz=UTC)` como fallback cuando no se proporciona,
evitando mezcla de timestamps naive/aware.

#### P3.4 — Changelog Renderer

**Archivo:** `src/licit/changelog/renderer.py`

Renderiza lista de `ConfigChange` en Markdown o JSON.

**Formato Markdown:**
- Header `# Agent Config Changelog`
- Summary con conteos por severidad
- Secciones por archivo, ordenadas alfabéticamente
- Dentro de cada archivo: ordenado por severidad (MAJOR primero), luego timestamp descendente
- Footer con timestamp UTC de generación

**Formato JSON:**
- Objeto `{"changes": [...]}` con records individuales
- `ensure_ascii=False` para soporte unicode (ñ, ü, 日本語, etc.)
- Campos: file_path, field_path, old_value, new_value, severity, description, timestamp, commit_sha

#### P3.5 — CLI Integration

**Archivo:** `src/licit/cli.py` (modificado)

El comando `changelog` ahora usa las implementaciones reales:
- Imports directos de `ConfigWatcher`, `ChangeClassifier`, `ChangelogRenderer`
- Import de `ConfigChange` en core models
- Pipeline: watcher.get_config_history() → classifier.classify_changes() → renderer.render()
- `--format json` para output JSON
- `--since` para limitar rango temporal
- `click.echo(output)` antes de file write (output siempre visible)
- `try/except OSError` en file write con mensaje de warning

### Tests (93 total de changelog)

| Archivo | # Tests | Qué cubre |
|---------|---------|-----------|
| `tests/test_changelog/test_watcher.py` | 12 | Git history retrieval, glob patterns, edge cases, deleted files, deduplication |
| `tests/test_changelog/test_differ.py` | 19 | YAML/JSON/MD/text diffs, non-dict roots, code blocks, empty, parse errors |
| `tests/test_changelog/test_classifier.py` | 22 | Field matching, segment-based matching, all severities, escalation, truncation |
| `tests/test_changelog/test_renderer.py` | 10 | Markdown/JSON rendering, grouping, sorting, empty changes, summary |
| `tests/test_changelog/test_integration.py` | 3 | Full pipeline markdown, JSON, empty case |
| `tests/test_changelog/test_qa_edge_cases.py` | 27 | CLI commands, no-git, unicode, timezone, differ/classifier/renderer edges, imports |

### Fixtures de test

| Archivo | Contenido |
|---------|-----------|
| `tests/test_changelog/fixtures/claude_md_v1.md` | CLAUDE.md inicial con secciones Instructions y Rules |
| `tests/test_changelog/fixtures/claude_md_v2.md` | CLAUDE.md modificado con Instructions cambiado, Rules editado, sección Model añadida |
| `tests/test_changelog/fixtures/cursorrules_v1.txt` | Reglas TypeScript para testing de diff texto plano |
| `tests/test_changelog/fixtures/architect_config_v1.yaml` | Config YAML con claude-sonnet-4, guardrails, budget |
| `tests/test_changelog/fixtures/architect_config_v2.yaml` | Config YAML con claude-opus-4, guardrails expandidos, budget mayor |

### Decisiones Técnicas

1. **Segment-based field matching** — `_field_matches()` compara trailing segments en lugar de usar `in` substring. Esto evita que `model_config` dispare MAJOR por contener "model". El patrón `model` solo matchea si el último segmento del path es exactamente `model`.

2. **`_coerce_to_dict()` para roots no-dict** — YAML y JSON permiten roots que son listas o escalares. En vez de descartarlos como `{}`, se wrappean como `{"(root)": data}` para que el diff reporte el cambio.

3. **Fenced code block awareness** — `_parse_md_sections()` trackea el estado `in_code_block` para no interpretar `# heading` dentro de bloques ``` como secciones reales. Importante para CLAUDE.md que frecuentemente contiene ejemplos de código.

4. **Size guard en git show** — `_MAX_CONTENT_BYTES = 1_048_576` previene OOM si un archivo binario fue accidentalmente tracked como config. La limitación es que subprocess carga todo en memoria antes de medir, pero 1MB es suficiente para cualquier config real.

5. **Removal escalation** — Eliminar un campo MINOR (ej: borrar `guardrails`) se escalará a MAJOR porque la eliminación de controles de seguridad es un cambio de mayor impacto que modificarlos.

6. **UTC timestamps everywhere** — Usa `from datetime import UTC` (Python 3.12+) y `datetime.now(tz=UTC)` en todos los fallbacks. Git timestamps son timezone-aware (ISO 8601 con offset); mantener todo aware evita `TypeError` en sort.

### QA Hardening (post-implementación)

Se realizó una revisión de QA completa: verificación estática (`ruff --select ALL`,
`mypy --strict`), análisis profundo de código, ejecución de tests existentes, escritura
de tests adicionales de edge cases, y prueba de integración end-to-end con git repo real.

#### Bugs encontrados y corregidos

| # | Severidad | Archivo | Problema | Corrección |
|---|-----------|---------|----------|------------|
| 1 | **Alta** | `classifier.py` | `"model" in field_lower` causaba false MAJOR en `model_config`, `system_model` | Reemplazado con `_field_matches()` segment-based matching |
| 2 | **Alta** | `differ.py` | Non-dict YAML/JSON roots (ej: `[item1, item2]`) se descartaban como `{}` | Reemplazado con `_coerce_to_dict()` wrapping como `{"(root)": data}` |
| 3 | **Alta** | `watcher.py` | `git show` sin límite de tamaño podía cargar GBs de contenido binario | Añadido `_MAX_CONTENT_BYTES = 1_048_576` guard |
| 4 | **Alta** | `classifier.py` + `renderer.py` | `datetime.now()` sin timezone (DTZ005) — mezcla naive/aware en sort podía causar `TypeError` | Cambiado a `datetime.now(tz=UTC)` con `from datetime import UTC` |
| 5 | **Media** | `cli.py` | `Path.write_text()` sin manejo de `OSError` — crash si directorio no writable | Wrapped en `try/except OSError`, echo antes de write |
| 6 | **Media** | `watcher.py` | `_file_has_git_history()` no logueaba en timeout o failure | Añadido `logger.debug` para ambos paths |
| 7 | **Baja** | `differ.py` | Headings dentro de fenced code blocks (```) se parseaban como secciones reales | Añadido `in_code_block` tracking en `_parse_md_sections()` |

#### Tests de QA añadidos (27 nuevos en edge cases)

**Archivo:** `tests/test_changelog/test_qa_edge_cases.py`

| Clase | # Tests | Cobertura |
|-------|---------|-----------|
| `TestChangelogCLI` | 3 | CLI sin git repo, CLI con git real, CLI JSON format |
| `TestWatcherNoGit` | 2 | Sin git → empty, get_watched_files sin git |
| `TestWatcherSingleCommit` | 2 | 1 commit → 1 snapshot, 1 snapshot → 0 diffs |
| `TestUnicodeHandling` | 4 | Unicode en YAML, Markdown, JSON render, MD render |
| `TestTimezoneHandling` | 2 | Timestamps aware en sort, default timestamp es UTC |
| `TestDifferEdgeCases` | 5 | Empty strings, empty→populated, dict→scalar, whitespace, JSON empty |
| `TestClassifierEdgeCases` | 2 | `section:Model` es MINOR, empty content |
| `TestRendererEdgeCases` | 2 | Descripción larga, null values en JSON |
| `TestImportSafety` | 4 | Imports sin circular deps (watcher, differ, classifier, renderer) |

#### Verificación estática final

| Herramienta | Resultado |
|-------------|-----------|
| `ruff check src/licit/` | ✅ 0 errores |
| `mypy --strict src/licit/` | ✅ 0 errores en 33 archivos |
| `pytest tests/` | ✅ 373 tests passed |
| E2E real git repo | ✅ Pipeline completo verificado |

#### Riesgos residuales

| Riesgo | Impacto | Nota |
|--------|---------|------|
| `git show` carga todo en memoria antes de medir tamaño | Bajo | subprocess no soporta streaming con `capture_output=True`; guard de 1MB mitiga caso común |
| `_parse_md_sections` no soporta headings setext (`===`/`---`) | Bajo | Solo ATX (`#`); configs AI usan ATX universalmente |
| Watch patterns con `**` recursivo no testados E2E con git history | Bajo | `Path.glob()` soporta `**`; `_file_has_git_history` recibe path resuelto |

---

## Phase 4 — EU AI Act Framework (COMPLETADA)

### Objetivo
Implementar el framework de EU AI Act completo: protocolo base de frameworks, registro,
11 requisitos evaluables (artículos 9-27 + Annex IV), evaluador por artículo con scoring,
generador FRIA interactivo con auto-detección, generador Annex IV auto-poblado desde
metadatos del proyecto, y templates Jinja2 para los reportes.

### Módulos Implementados

#### P4.1 — Framework Protocol + Registry

**Archivos:**
- `src/licit/frameworks/base.py` — Protocol `ComplianceFramework`
- `src/licit/frameworks/registry.py` — `FrameworkRegistry` con singleton global

**Protocol `ComplianceFramework`:**
- `@runtime_checkable` — Permite verificación con `isinstance()` en runtime
- 3 propiedades: `name`, `version`, `description`
- 2 métodos: `get_requirements()` → `list[ControlRequirement]`, `evaluate(context, evidence)` → `list[ControlResult]`
- Imports en `TYPE_CHECKING` block para evitar dependencias circulares

**`FrameworkRegistry`:**
- Dict-based: `register()`, `get()`, `list_all()`, `names()`
- Singleton global via `_registry` + `get_registry()`
- Infraestructura para Phase 6 (unified report enumera frameworks registrados)
- Logging structlog en registro de frameworks

#### P4.2 — EU AI Act Requirements

**Archivo:** `src/licit/frameworks/eu_ai_act/requirements.py`

11 requisitos como `ControlRequirement` dataclasses con constantes de framework:

| ID | Artículo | Nombre | Categoría |
|----|----------|--------|-----------|
| ART-9-1 | Article 9(1) | Risk Management System | risk-management |
| ART-10-1 | Article 10(1) | Data Governance | data-governance |
| ART-12-1 | Article 12(1) | Record Keeping — Automatic Logging | record-keeping |
| ART-13-1 | Article 13(1) | Transparency — Information for Deployers | transparency |
| ART-14-1 | Article 14(1) | Human Oversight | human-oversight |
| ART-14-4a | Article 14(4)(a) | Human Oversight — Understand Capabilities | human-oversight |
| ART-14-4d | Article 14(4)(d) | Human Oversight — Ability to Intervene | human-oversight |
| ART-26-1 | Article 26(1) | Deployer — Use in Accordance with Instructions | deployer-obligations |
| ART-26-5 | Article 26(5) | Deployer — Monitoring | deployer-obligations |
| ART-27-1 | Article 27(1) | Fundamental Rights Impact Assessment (FRIA) | fria |
| ANNEX-IV | Annex IV | Technical Documentation | documentation |

**Helpers:** `get_requirement(id)` y `get_requirements_by_category(category)`.

#### P4.3 — EU AI Act Evaluator

**Archivo:** `src/licit/frameworks/eu_ai_act/evaluator.py`

`EUAIActEvaluator` — Implementa `ComplianceFramework` Protocol. Evalúa los 11 artículos
usando dispatch dinámico: `getattr(self, f"_eval_{id.lower().replace('-', '_')}")`.

**Scoring por artículo:**

| Artículo | Indicadores (score) | Compliant at | Partial at |
|----------|-------------------|-------------|------------|
| Art. 9 | Guardrails +1, quality gates +1, budget +1, security scanning +1 (max 4) | 3+ | 1+ |
| Art. 10 | Siempre PARTIAL (deployer no entrena modelos) | — | — |
| Art. 12 | Git +1, audit trail +2, provenance +1, OTel +1 (max 5) | 3+ | 1+ |
| Art. 13 | Annex IV +2, changelog +1, traceability +1 (max 4) | 2+ | 1+ |
| Art. 14 | Dry-run +1, human review +2, quality gates +1, budget +1 (max 5) | 3+ | 1+ |
| Art. 14(4)(a) | Delega a Art. 14(1) | — | — |
| Art. 14(4)(d) | Dry-run + rollback → COMPLIANT, else PARTIAL | — | — |
| Art. 26(1) | Agent configs presentes → COMPLIANT, else PARTIAL | — | — |
| Art. 26(5) | Delega a Art. 12(1) | — | — |
| Art. 27 | FRIA presente → COMPLIANT, else NON_COMPLIANT | — | — |
| Annex IV | Documentación presente → COMPLIANT, else NON_COMPLIANT | — | — |

**`_score_to_status(score, *, compliant_at, partial_at)` helper:**
- score >= compliant_at → COMPLIANT
- score >= partial_at → PARTIAL
- else → NON_COMPLIANT

**Robustez:**
- `provenance_stats.get("ai_percentage")` con `isinstance` check + `logger.debug` en type inesperado
- Métodos delegantes (`_eval_art_14_4a`, `_eval_art_26_5`) preservan el `req` del caller
- Cada método genera recomendaciones accionables con comandos licit concretos
- Scoring rationale documentado en docstring de cada método

#### P4.4 — FRIA Generator

**Archivo:** `src/licit/frameworks/eu_ai_act/fria.py`

`FRIAGenerator` — Genera Fundamental Rights Impact Assessment interactivo per Art. 27.

**5 pasos con 16 preguntas:**

| Paso | Título | Preguntas | Auto-detectable |
|------|--------|-----------|-----------------|
| 1 | System Description | 5 | system_purpose, ai_technology, models_used, human_review |
| 2 | Fundamental Rights Identification | 4 | — |
| 3 | Impact Assessment | 3 | — |
| 4 | Mitigation Measures | 5 | guardrails, security_scanning, testing, audit_trail |
| 5 | Monitoring & Review | 3 | — |

**Auto-detección (8 campos):**

| Campo | Fuente | Ejemplo |
|-------|--------|---------|
| system_purpose | `has_architect` / `agent_configs` | "Autonomous code generation using AI agents (architect)" |
| ai_technology | `has_architect` → headless, else interactive | "Autonomous AI agent (headless)" |
| models_used | Lee `architect_config_path` → `llm.model` | "claude-sonnet-4" |
| human_review | `ev.has_human_review_gate` | "Yes -- all AI-generated code requires human review" |
| guardrails | `ev.has_guardrails` + counts | "5 guardrail rules, 2 quality gates, budget limits" |
| security_scanning | `ctx.security.has_vigil/semgrep/snyk/codeql` | "vigil (AI-specific security), Semgrep (SAST)" |
| testing | `ctx.test_framework` + `ctx.test_dirs` | "pytest (tests)" |
| audit_trail | git + audit trail + provenance | "Git history (100 commits), Code provenance tracking (licit)" |

**Dispatch de detectores:** Dict de `Callable[[], str | None]` mapea campo → método `_detect_*`.

**Métodos públicos:**
- `run_interactive()` → `dict[str, Any]` — Cuestionario con click.echo/prompt/confirm
- `generate_report(responses, output_path)` — Jinja2 render a Markdown
- `save_data(responses, data_path)` — JSON persistence

**Robustez:**
- `_detect_models_used`: `try/except (OSError, YAMLError)` con logging
- Versión via `licit.__version__` (no hardcoded)
- `encoding="utf-8"` en toda I/O de archivos
- `Path.parent.mkdir(parents=True, exist_ok=True)` antes de write

#### P4.5 — Annex IV Generator

**Archivo:** `src/licit/frameworks/eu_ai_act/annex_iv.py`

`AnnexIVGenerator` — Auto-genera documentación técnica Annex IV desde metadatos del proyecto.

**`_collect_data()` — 27 variables de template:**
- Organización, producto, timestamp
- Lenguajes, frameworks, package managers
- Agent configs y tipos, has_architect
- CI/CD platform y config path
- Test framework y dirs
- Security tools (vigil, Semgrep, Snyk, CodeQL, Trivy)
- Git stats (commits, contributors)
- Provenance (has + ai_percentage)
- Audit trail (has + count), changelog, FRIA
- Guardrails (has + count), quality gates (has + count)
- Budget limits, human review gate

**6 secciones del documento:**
1. General Description — Intended purpose, AI components, languages/frameworks
2. Development Process — Version control, AI provenance, agent config files
3. Monitoring, Functioning and Control — CI/CD, audit trail, changelog tracking
4. Risk Management — Guardrails, quality gates, budget, human oversight, FRIA
5. Testing and Validation — Test framework, security scanning tools
6. Changes and Lifecycle — Resumen de mecanismos de tracking

**Recomendaciones automáticas:** Cada sección sin evidencia genera una recomendación
accionable con comando licit concreto (ej: "Run `licit trace` to begin tracking code provenance").

#### P4.6 — Jinja2 Templates

**Archivos:**
- `src/licit/frameworks/eu_ai_act/templates/fria_template.md.j2`
- `src/licit/frameworks/eu_ai_act/templates/annex_iv_template.md.j2`
- `src/licit/frameworks/eu_ai_act/templates/report_section.md.j2`

**FRIA template:**
- Header table (project, generated, version)
- Iteración sobre steps/questions con `responses.get(q.field, '*Not provided*')`
- Summary section con review schedule
- Acceso seguro: `responses.get('key', default)` en todos los campos

**Annex IV template:**
- Whitespace-controlled con `{%-`/`-%}` para output limpio (sin blank lines excesivos)
- Conditional blocks para cada sección
- `{{ "%.1f" | format(ai_percentage) }}%` para porcentaje de provenance
- `{{ languages | join(', ') }}` para listas

**Report section template:**
- Summary table (compliant/partial/non-compliant/n-a/not-evaluated + compliance rate)
- Per-requirement details con status, article ref, evidence, recommendations

#### P4.7 — CLI Integration

**Archivo:** `src/licit/cli.py` (modificado)

Cambios:
- `licit fria`: Import directo de `FRIAGenerator` (sin `# type: ignore`)
- `licit annex-iv`: Import directo de `AnnexIVGenerator` (sin `# type: ignore`)
- `_get_frameworks()`: Import directo de `EUAIActEvaluator` (sin `# type: ignore`)
- Types: `FRIAGenerator` y `AnnexIVGenerator` tipados (sin `Any`)

#### P4.8 — Test Infrastructure Updates

**Archivo:** `tests/conftest.py` (modificado)

- `make_context()`: Nuevo parámetro `security: SecurityTooling | None`
- `make_evidence()`: 6 nuevos parámetros: `provenance_stats`, `fria_path`, `annex_iv_path`, `audit_entry_count`, `changelog_entry_count`

### Tests (124 total de Phase 4)

| Archivo | # Tests | Qué cubre |
|---------|---------|-----------|
| `tests/test_frameworks/test_eu_ai_act/test_evaluator.py` | 32 | Properties (4), full evaluation (3), Art. 9 (4), Art. 10 (1), Art. 12 (4), Art. 13 (3), Art. 14 (6), Art. 26 (3), Art. 27 (2), Annex IV (2) |
| `tests/test_frameworks/test_eu_ai_act/test_fria.py` | 23 | Steps structure (5), auto-detection (13), report generation (3), data saving (2) |
| `tests/test_frameworks/test_eu_ai_act/test_annex_iv.py` | 17 | Generation (3), content sections (12), minimal project (2) |
| `tests/test_frameworks/test_eu_ai_act/test_requirements.py` | 9 | Data integrity (3), get_requirement (3), get_by_category (3) |
| `tests/test_frameworks/test_eu_ai_act/test_qa_edge_cases.py` | 43 | Protocol conformance (3), _score_to_status (7), evaluator edges (8), FRIA edges (8), Annex IV edges (5), registry (5), CLI (2), requirements integrity (3), cross-module (2) |

### Decisiones Técnicas

1. **`@property` para Protocol y evaluator** — `name`, `version`, `description` como `@property`
   en la Protocol y en `EUAIActEvaluator`. Más explícito que class attributes, y compatible
   con mypy strict + structural typing.

2. **Dynamic method dispatch** — `getattr(self, f"_eval_{id}")` con fallback a `NOT_EVALUATED`.
   Permite agregar artículos nuevos con solo añadir un método `_eval_*` y un `ControlRequirement`.
   Test `test_all_requirement_ids_have_evaluator_method` verifica que no haya gaps.

3. **Scoring con thresholds configurables** — `_score_to_status(score, compliant_at=N, partial_at=M)`
   permite que cada artículo tenga umbrales diferentes según cuántos indicadores existen.
   Art. 13 solo necesita score 2 (Annex IV sola basta) vs. Art. 9 necesita 3.

4. **FRIA auto-detect via callable dispatch** — Dict `{field: Callable}` en lugar de cadena
   if/elif. Más extensible: agregar campo = agregar método + entrada en dict.

5. **Templates con whitespace control** — `{%-`/`-%}` en Annex IV template para evitar
   blank lines excesivos. FRIA template usa `responses.get()` consistentemente para safety.

6. **Registry como infraestructura** — `FrameworkRegistry` se crea pero no se usa aún.
   Phase 6 (unified report) lo usará para enumerar frameworks. No es dead code: es
   infraestructura planificada según el dependency graph (P4.1 → P6.1).

### QA Hardening (post-implementación)

Se realizó una revisión de QA completa: verificación estática (`ruff --select ALL` +
`mypy --strict`), análisis profundo de cada archivo, ejecución de 454 tests existentes,
escritura de 43 tests de edge cases, y prueba de integración end-to-end con git repo real.

#### Bugs encontrados y corregidos

| # | Severidad | Archivo | Problema | Corrección |
|---|-----------|---------|----------|------------|
| 1 | **Media** | `fria_template.md.j2` | `{{ responses.responsible_person }}` — acceso directo a dict sin `.get()` dentro de bloque `{% if %}` guard | Cambiado a `{{ responses.get('responsible_person', '') }}` |
| 2 | **Media** | `annex_iv_template.md.j2` | Blank lines excesivos entre secciones por whitespace de Jinja2 | Añadido `{%-`/`-%}` whitespace control en bloques condicionales |

#### Tests de QA añadidos (43 nuevos)

**Archivo:** `tests/test_frameworks/test_eu_ai_act/test_qa_edge_cases.py`

| Clase | # Tests | Cobertura |
|-------|---------|-----------|
| `TestProtocolConformance` | 3 | `isinstance()` check, evaluate signature, get_requirements types |
| `TestScoreToStatus` | 7 | Boundaries: 0, partial_at, between, compliant_at, above, negative, equal thresholds |
| `TestEvaluatorEdgeCases` | 8 | provenance_stats string/None/missing, all-compliant scenario, all-non-compliant, delegation preserves requirement ID, recommendations are actionable strings |
| `TestFRIAEdgeCases` | 8 | Empty responses, unicode, save/load roundtrip, YAML real/malformado/missing/sin-llm-key, question ID sequential |
| `TestAnnexIVEdgeCases` | 5 | Unicode in org/product, empty strings, pipe chars, percentage 0 and 100 |
| `TestFrameworkRegistry` | 5 | Register/get, missing, list_all, names, empty |
| `TestCLIIntegration` | 2 | `verify --framework eu-ai-act` exit code 1, output contains expected text |
| `TestRequirementsIntegrity` | 3 | All IDs have evaluator method, framework consistent, categories valid |
| `TestCrossModule` | 2 | ControlResult → GapItem compatibility, ControlResult → ComplianceSummary |

#### Verificación estática final

| Herramienta | Resultado |
|-------------|-----------|
| `ruff check src/licit/` | ✅ 0 errores |
| `mypy --strict src/licit/` | ✅ 0 errores en 39 archivos |
| `pytest tests/` | ✅ 497 tests passed |
| E2E real git repo | ✅ init → trace → annex-iv → verify pipeline completo |

#### Riesgos residuales

| Riesgo | Impacto | Nota |
|--------|---------|------|
| Pipe char `\|` en organization/product name rompe tabla Markdown en Annex IV | Bajo | Documentado por test; org names raramente contienen `\|` |
| FRIA `run_interactive()` sin unit tests | Bajo | Requiere terminal I/O; auto-detect, report gen, y save están cubiertos; flujo interactivo verificado manualmente |
| `autoescape=False` en Jinja2 Environment | Bajo | Correcto para Markdown; Phase 6 HTML reporter deberá usar `True` |
| `registry.py` sin uso activo | Info | Infraestructura para Phase 6; no es dead code |

---

## Phase 5 — OWASP Agentic Top 10 (COMPLETADA)

### Objetivo
Implementar el framework OWASP Agentic Top 10: 10 requisitos de seguridad para agentes de IA,
evaluador con scoring por control, y template Jinja2 para reportes — siguiendo exactamente
los patrones establecidos en Phase 4 (EU AI Act).

### Módulos Implementados

#### P5.1 — OWASP Agentic Requirements

**Archivo:** `src/licit/frameworks/owasp_agentic/requirements.py`

10 requisitos como `ControlRequirement` dataclasses:

| ID | Referencia | Nombre | Categoría |
|----|-----------|--------|-----------|
| ASI01 | ASI-01 | Excessive Agency | access-control |
| ASI02 | ASI-02 | Prompt Injection | input-security |
| ASI03 | ASI-03 | Supply Chain Vulnerabilities | supply-chain |
| ASI04 | ASI-04 | Insufficient Logging and Monitoring | observability |
| ASI05 | ASI-05 | Improper Output Handling | output-security |
| ASI06 | ASI-06 | Lack of Human Oversight | human-oversight |
| ASI07 | ASI-07 | Insufficient Sandboxing | isolation |
| ASI08 | ASI-08 | Unbounded Resource Consumption | resource-limits |
| ASI09 | ASI-09 | Poor Error Handling | error-handling |
| ASI10 | ASI-10 | Sensitive Data Exposure | data-protection |

**Constantes:** `OWASP_AGENTIC_FRAMEWORK = "owasp-agentic"`, `OWASP_AGENTIC_VERSION = "2025"`

**Helpers:** `get_requirement(id)` y `get_requirements_by_category(category)`.

#### P5.2 — OWASP Agentic Evaluator

**Archivo:** `src/licit/frameworks/owasp_agentic/evaluator.py`

`OWASPAgenticEvaluator` — Implementa `ComplianceFramework` Protocol. Evalúa los 10 controles
usando dispatch dinámico: `getattr(self, f"_eval_{id.lower()}")`.

**Scoring por control:**

| Control | Indicadores (score) | Compliant at | Partial at |
|---------|-------------------|-------------|------------|
| ASI01 | Guardrails +1, quality gates +1, budget +1, agent configs +1 (max 4) | 3+ | 1+ |
| ASI02 | vigil +2, guardrails +1, human review +1 (max 4) | 3+ | 1+ |
| ASI03 | SCA tools (Snyk/Semgrep/CodeQL/Trivy) +2, changelog +1, agent configs +1 (max 4) | 3+ | 1+ |
| ASI04 | Git +1, audit trail +2, provenance +1, OTel +1 (max 5) | 3+ | 1+ |
| ASI05 | Human review +2, quality gates +1, test framework +1 (max 4) | 3+ | 1+ |
| ASI06 | Human review +2, dry-run +1, quality gates +1, rollback +1 (max 5) | 3+ | 1+ |
| ASI07 | Guardrails +2, CI/CD +1, agent configs +1 (max 4) | 3+ | 1+ |
| ASI08 | Budget limits +2, quality gates +1 (max 3) | 2+ | 1+ |
| ASI09 | Test suite +1, CI/CD +1, rollback +1 (max 3) | 2+ | 1+ |
| ASI10 | Guardrails +1, security scanning +2, agent configs +1 (max 4) | 3+ | 1+ |

**Helpers:**
- `_score_to_status(score, *, compliant_at, partial_at)` — Misma función que EU AI Act
- `_safe_float(value, *, field)` — Conversión segura con logging de tipos inesperados

**Robustez:**
- Thresholds ajustados por control: ASI08 y ASI09 usan `compliant_at=2` (menos señales disponibles)
- `guardrail_count=0` con `has_guardrails=True` produce "configured" en vez de "0 rules"
- Cada método genera recomendaciones accionables específicas al riesgo OWASP
- `_safe_float` acepta parámetro `field` para logging contextual (no hardcoded)

#### P5.3 — Jinja2 Template

**Archivo:** `src/licit/frameworks/owasp_agentic/templates/report_section.md.j2`

Template alineado al formato exacto de EU AI Act (`report_section.md.j2`):
- Summary table (compliant/partial/non-compliant/n-a/not-evaluated + compliance rate)
- Per-requirement details con status, reference, evidence, recommendations
- Mismo nivel de headings (`### `), mismo formato de status (`{{ result.status }}`)

#### P5.4 — CLI Integration

**Archivo:** `src/licit/cli.py` (modificado)

- `_get_frameworks()`: Import directo de `OWASPAgenticEvaluator` (eliminado `# type: ignore[import-not-found]`)
- `licit verify --framework owasp`, `licit report --framework owasp`, `licit gaps --framework owasp` ahora funcionales
- `licit init --framework owasp` configura solo OWASP

#### P5.5 — Test Infrastructure Updates

**Archivo:** `tests/conftest.py` (modificado)

`make_evidence()` expandido con 5 nuevos parámetros para cobertura completa de `EvidenceBundle`:
- `has_otel: bool`
- `has_requirements_traceability: bool`
- `security_findings_total: int`
- `security_findings_critical: int`
- `security_findings_high: int`

### Tests (103 total de Phase 5)

| Archivo | # Tests | Qué cubre |
|---------|---------|-----------|
| `tests/test_frameworks/test_owasp/test_evaluator.py` | 40 | Properties (4), full evaluation (5), ASI01-ASI10 compliant/partial/non-compliant (31) |
| `tests/test_frameworks/test_owasp/test_requirements.py` | 15 | Data integrity (9), get_requirement (3), get_by_category (3) |
| `tests/test_frameworks/test_owasp/test_qa_edge_cases.py` | 48 | Protocol conformance (3), _score_to_status boundaries (8), _safe_float robustness (8), evaluator edge cases (17), registry interop (3), CLI integration (3), requirements integrity (4), cross-module (3) |

### Decisiones Técnicas

1. **OWASP version "2025"** — El plan referenciaba `top10_2026.json` pero la referencia real
   del OWASP Agentic Top 10 es 2025. Se usó el año correcto.

2. **Requirements como código, no JSON** — Definidos como constantes Python en `requirements.py`
   (mismo patrón que EU AI Act), no como archivo JSON externo. Más type-safe y testeable.

3. **Thresholds variables por control** — ASI08 (max score 3) y ASI09 (max score 3) usan
   `compliant_at=2` porque tienen menos señales de evidencia disponibles. Los demás usan
   `compliant_at=3` con max scores de 4-5.

4. **Scoring basado en presencia, no en hallazgos** — El evaluador verifica que las herramientas
   de seguridad *existan* (has_vigil, has_snyk), no qué *encontraron* (security_findings_*).
   Los findings son relevantes para Phase 6 (Gap Analyzer). Decisión consciente documentada con
   test negativo `test_security_findings_do_not_affect_scoring`.

5. **Template alineado con EU AI Act** — Inicialmente el template OWASP tenía formato distinto
   (em dash, `####` headings, `status.value`). QA detectó la inconsistencia y se alineó al
   formato exacto de EU AI Act para que Phase 6 los consuma uniformemente.

### QA Hardening (post-implementación)

Se realizó una revisión de QA completa: verificación estática (`ruff --select ALL` +
`mypy --strict`), análisis línea por línea de cada archivo, ejecución de 594 tests existentes,
escritura de 48 tests de edge cases, corrección de 3 bugs, y prueba de integración end-to-end
con git repo real.

#### Bugs encontrados y corregidos

| # | Severidad | Archivo | Problema | Corrección |
|---|-----------|---------|----------|------------|
| 1 | **Media** | `templates/report_section.md.j2` | Template inconsistente con EU AI Act: headers (`##` vs `###`), `status.value` vs `status`, em dash vs parentheses | Alineado al formato exacto de EU AI Act |
| 2 | **Baja** | `evaluator.py` | `_safe_float` hardcodeaba `field="ai_percentage"` en log — nombre genérico con log específico | Añadido parámetro `field` con default `"unknown"` |
| 3 | **Baja** | `evaluator.py` | `has_guardrails=True, guardrail_count=0` producía "0 rules" — misleading | Branch condicional: count>0 → "N rules", else → "configured" |

#### Tests de QA añadidos (48 nuevos)

**Archivo:** `tests/test_frameworks/test_owasp/test_qa_edge_cases.py`

| Clase | # Tests | Cobertura |
|-------|---------|-----------|
| `TestProtocolConformance` | 3 | `isinstance()` check, evaluate signature, get_requirements types |
| `TestScoreToStatus` | 8 | Boundaries: 0, partial, between, compliant, above, negative, equal thresholds, ASI08 thresholds |
| `TestSafeFloat` | 8 | int, float, zero, string, None, list, bool, negative float |
| `TestEvaluatorEdgeCases` | 17 | provenance_stats string/None/missing, OTel bonus, SCA tools listing, CI/CD platform display, test framework display, actionable recommendations, all-compliant 10/10, all-non-compliant 10/10, idempotency, compliant→empty recs, non-compliant→has recs, security_findings neutral, guardrail_count=0, template rendering |
| `TestFrameworkRegistry` | 3 | Register OWASP, register both frameworks, no ID collision |
| `TestCLIIntegration` | 3 | `verify --framework owasp`, `verify --framework all`, bare project exit code 1 |
| `TestRequirementsIntegrity` | 4 | All IDs have evaluator method, framework consistent, categories valid, IDs sequential |
| `TestCrossModule` | 3 | ControlResult → GapItem, ControlResult → ComplianceSummary, dual-framework evaluation |

#### Verificación estática final

| Herramienta | Resultado |
|-------------|-----------|
| `ruff check src/licit/` | 0 errores |
| `mypy --strict src/licit/` | 0 errores en 41 archivos |
| `pytest tests/` | 600 tests passed |
| E2E real git repo | `verify --framework owasp` → 1 compliant, 7 partial, 2 non-compliant (exit 1) |

#### Riesgos residuales

| Riesgo | Impacto | Nota |
|--------|---------|------|
| `security_findings_*` no usados en scoring | Diseño | Evaluador mide presencia de herramientas, no hallazgos; Phase 6 Gap Analyzer los usará |
| `_eval_asi06` y `_eval_asi08` no usan `ctx` | Cosmético | Dispatch pattern requiere firma uniforme `(req, ctx, ev)`; correcto |
| Overlap temático con EU AI Act (Human Oversight, Logging) | Diseño | Scoring diferente — OWASP enfoca seguridad, EU AI Act enfoca governance; frameworks independientes |

---

## Phase 6 — Reports + Gap Analyzer (COMPLETADA)

### Objetivo
Generar reportes de compliance unificados multi-framework en múltiples formatos
(Markdown, JSON, HTML), analizar gaps con recomendaciones accionables, e
integrar los comandos `report`, `gaps` y `verify` del CLI con los evaluadores
de Phase 4 y 5.

### Módulos Implementados

#### P6.1 — UnifiedReportGenerator

**Archivo:** `src/licit/reports/unified.py`

Orquesta la evaluación de múltiples frameworks y produce un reporte unificado:
- `UnifiedReport` dataclass con estadísticas agregadas cross-framework.
- `FrameworkReport` dataclass por cada framework evaluado (name, version, description, summary, results).
- `_evaluate_framework()` con exception handling — un framework que falla no impide la generación del reporte de los demás.
- `_summarize()` computa `ComplianceSummary` (compliant, partial, non-compliant, n/a, not-evaluated, compliance_rate%).
- `_compute_overall()` agrega estadísticas de todos los frameworks.
- Flags `include_evidence` y `include_recommendations` propagados desde `ReportConfig`.
- Timestamps UTC vía `datetime.now(tz=UTC)`.

#### P6.2 — GapAnalyzer

**Archivo:** `src/licit/reports/gap_analyzer.py`

Identifica requisitos no-cumplidos y genera recomendaciones accionables:
- Evalúa todos los frameworks, filtra resultados `NON_COMPLIANT` y `PARTIAL`.
- `_TOOL_SUGGESTIONS` — mapa de categoría → lista de herramientas sugeridas, cubriendo las 8 categorías EU AI Act y 10 categorías OWASP Agentic (17 keys en total, `human-oversight` compartida).
- `_EFFORT_MAP` — estimación de esfuerzo (`low`/`medium`/`high`) por categoría.
- Ordenamiento: non-compliant antes que partial, prioridad secuencial asignada.
- Fallback para categorías desconocidas: tools=[], effort="medium".
- Exception handling por framework — un evaluador que falla se skipea con logging.

#### P6.3 — Markdown Reporter

**Archivo:** `src/licit/reports/markdown.py`

Renderiza `UnifiedReport` como Markdown:
- Header con proyecto y timestamp.
- Tabla de resumen overall.
- Sección por framework con tabla de contadores y detalle por requisito.
- Iconos de estado: `[PASS]`, `[PARTIAL]`, `[FAIL]`, `[N/A]`, `[?]`.
- Evidence y recommendations condicionales según flags de config.
- Footer con link al repositorio.

#### P6.4 — JSON Reporter

**Archivo:** `src/licit/reports/json_fmt.py`

Renderiza `UnifiedReport` como JSON:
- Estructura: `project_name`, `generated_at`, `overall` (7 campos), `frameworks[]` con `summary` y `results[]`.
- Evidence y recommendations condicionales.
- `_json_default()` para serialización de `datetime`.
- `ensure_ascii=False` para soporte unicode.

#### P6.5 — HTML Reporter

**Archivo:** `src/licit/reports/html.py`

Renderiza `UnifiedReport` como HTML auto-contenido:
- Single-file sin dependencias externas (no CSS/JS externos).
- CSS inline con diseño responsive (max-width 960px).
- Badges de color por status: verde (compliant), ámbar (partial), rojo (non-compliant), gris (n/a, not-evaluated).
- `_esc()` escapa 5 caracteres HTML: `&`, `<`, `>`, `"`, `'` — previene XSS.
- Evidence y recommendations condicionales.

#### P6.6 — Terminal Summary

**Archivo:** `src/licit/reports/summary.py`

Imprime resumen compacto al terminal:
- `print_summary()` muestra tabla por framework con barra de progreso ASCII.
- `_progress_bar()` renderiza `[####............]` con porcentaje, clamped a [0, width].
- Totales overall al final.

#### P6.7 — CLI Integration

**Archivo:** `src/licit/cli.py` (modificado)

- `licit report` — genera reporte en 3 formatos con flag `--format` y output personalizable con `-o`.
- `licit gaps` — muestra gaps con iconos `[X]`/`[!]`, descripción, recomendación, y herramientas sugeridas.
- `licit verify` — gate CI/CD con exit codes 0 (compliant), 1 (non-compliant), 2 (partial).
- Eliminados todos los `# type: ignore[import-not-found]` — imports reales.
- `_get_frameworks()` helper compartido por los 3 comandos.

### Tests Implementados

| Archivo | Tests | Cobertura |
|---------|-------|-----------|
| `test_unified.py` | 12 | Generación vacía/single/multi framework, totales, compliance rate, flags, exceptions |
| `test_gap_analyzer.py` | 15 | Gaps vacío/minimal/full, sorting, prioridad, effort, descriptions, OWASP, multi-framework, exceptions, categorías |
| `test_markdown.py` | 10 | Proyecto, secciones, summary, iconos, evidence, recommendations, footer, tablas, vacío |
| `test_json_fmt.py` | 10 | JSON válido, proyecto, overall, frameworks, fields, evidence, recommendations, counts, vacío, timestamp |
| `test_html.py` | 12 | HTML válido, proyecto, secciones, style, badges, escape (5 chars + single quotes), evidence, recommendations, footer, self-contained, vacío |
| `test_summary.py` | 11 | Progress bar (0%/50%/100%/clamped), prints (proyecto, frameworks, overall, bar, vacío) |
| `test_qa_edge_cases.py` | 26 | Category mapping completeness (7), unicode (3), boundary inputs (7), cross-module integration (5), HTML escaping (4) |
| `test_cli.py` (añadidos) | 10 | report markdown/json/html/custom output/summary, gaps output/recommendations, verify exit codes |
| **Total Phase 6** | **106** | |

### Resultados de QA

#### Bugs encontrados y corregidos

| # | Severidad | Descripción | Corrección |
|---|-----------|-------------|------------|
| 1 | **CRITICAL** | `gap_analyzer.py`: 8 de 10 categorías OWASP no coincidían con las definidas en `owasp_agentic/requirements.py`. Usaba nombres inventados (`excessive-agency`, `prompt-injection`, `sandboxing`, etc.) en vez de los reales (`access-control`, `input-security`, `isolation`, etc.). Resultado: OWASP gaps sin tool suggestions ni effort correcto. | Reescrito `_TOOL_SUGGESTIONS` y `_EFFORT_MAP` con las categorías exactas de `requirements.py`. Añadidos 7 tests que validan completeness cross-referencing ambos módulos. |
| 2 | **HIGH** | `unified.py`/`gap_analyzer.py`: Sin exception handling en llamadas a `fw.evaluate()`. Un evaluador que lanza excepción crasheaba todo el reporte o gap analysis. | `try/except Exception` con `logger.exception()`. Unified retorna `None` (framework skipped). GapAnalyzer hace `continue`. Tests con `BrokenEvaluator`. |
| 3 | **HIGH** | Sin tests CLI de integración para `report`, `gaps`, `verify`. Los comandos estaban en producción sin ningún test end-to-end. | 10 tests CLI: 3 formatos de report, custom output, summary print, gaps con recomendaciones, verify exit codes. |
| 4 | **MEDIUM** | `html.py _esc()`: No escapaba single quotes (`'`), riesgo XSS si atributos HTML usan single quotes. | Añadido `.replace("'", "&#39;")`. Test de verificación. |
| 5 | **MEDIUM** | `_TOOL_SUGGESTIONS["data-governance"]` estaba vacío — gaps de data governance no sugerían herramientas. | Añadido `"licit annex-iv (document data practices)"`. |
| 6 | **LOW** | `markdown.py`, `json_fmt.py`, `html.py`: importaban `structlog` + creaban logger sin usarlo. | Eliminados imports y `logger` no usados. |
| 7 | **LOW** | `json_fmt.py`: `_framework_to_dict(fw: Any, ...)` usaba `Any` en vez del tipo correcto. | Cambiado a `fw: FrameworkReport` con `TYPE_CHECKING` import. |

#### Riesgos residuales

| Riesgo | Severidad | Nota |
|--------|-----------|------|
| `human-oversight` es categoría compartida entre EU AI Act y OWASP (misma key, mismos tools sugeridos) | Low | Los tools son razonables para ambos contextos (dry-run, branch protection) |
| Si se añade un nuevo framework con categorías nuevas sin actualizar `gap_analyzer.py`, fallback es tools=[] y effort="medium" | Low | Los tests `TestCategoryMappingCompleteness` detectan esto automáticamente al importar requirements |

### Checklist de Verificación

- [x] Todos los archivos creados y funcionales
- [x] `pytest tests/ -q` — 706 tests, todos pasan
- [x] `ruff check src/licit/` — Sin errores
- [x] `mypy src/licit/ --strict` — Sin errores (47 archivos)
- [x] `python -m licit --help` — 10 comandos visibles
- [x] `licit report` genera Markdown, JSON y HTML correctos
- [x] `licit gaps` muestra gaps con tools y effort correctos (EU AI Act + OWASP)
- [x] `licit verify` retorna exit codes 0/1/2 correctos
- [x] E2E manual: init → trace → report (3 formatos) → gaps → verify en proyecto fake
- [x] Exception handling: framework que crashea no rompe el reporte
- [x] HTML XSS-safe: 5 caracteres escapados
- [x] Categorías OWASP verificadas contra `requirements.py` con tests automáticos

---

## Phase 7 — Connectors + Integration (COMPLETADA + QA)

### Objetivo
Implementar los conectores formales para architect y vigil, el test de integración end-to-end,
pulir el CLI, y crear la configuración de ejemplo `.licit.example.yaml`.

### Módulos Implementados

#### P7.1 — Connector Protocol

**Archivo:** `src/licit/connectors/base.py`

Define la interfaz formal para todos los connectors:
- `Connector` Protocol (`@runtime_checkable`): `name`, `enabled`, `available()`, `collect(evidence)`.
- `ConnectorResult` dataclass con `connector_name`, `files_read`, `errors`.
- `success` como `@property` computado: `files_read > 0 and len(errors) == 0`.
- `has_errors` property para chequeo rápido.
- `EvidenceBundle` importado solo bajo `TYPE_CHECKING` para evitar circular import.

#### P7.2 — Architect Connector

**Archivo:** `src/licit/connectors/architect.py`

Lee 3 fuentes de datos de architect:
- **Reports** (`_read_reports`): JSON files en `reports_dir`, parsea a `ArchitectReport` dataclass con task_id, status, model, cost, files_changed, timestamp. Cada campo validado con `isinstance`.
- **Audit log** (`_read_audit_log`): JSONL append-only, parsea a `AuditEntry` dataclass. Líneas malformadas registran error pero no abortan.
- **Config** (`_read_config`): YAML con guardrails, quality_gates, budget_usd, dry_run, rollback. `guardrail_count` usa `+=` (aditivo, no sobreescribe).
- `available()` checa si `reports_dir` o `config_path` existen en disco.
- Logging con structlog en cada operación.

#### P7.3 — Vigil Connector

**Archivo:** `src/licit/connectors/vigil.py`

Lee SARIF security findings y SBOM:
- **SARIF** (`_read_sarif`): parsea formato SARIF 2.1.0 — runs, results, locations. Cuenta findings por severidad (error→critical, warning→high, note→medium, else→low).
- `_parse_run` refactorizado en 3 métodos: `_extract_tool_name`, `_parse_finding`, `_extract_location` — complejidad reducida de C901/18 a métodos < C901/10.
- `_resolve_sarif_paths`: soporta path explícito (archivo o directorio), auto-detected SARIF files del ProjectContext, y deduplicación.
- **SBOM** (`_read_sbom`): valida CycloneDX JSON, cuenta como file_read. V0 no enrichece EvidenceBundle (documentado para V1 con campos supply-chain).
- Parsea **todos** los SARIF runs sin filtrar por tool name (consistente con el inline path).

#### P7.4 — EvidenceCollector Refactorizado

**Archivo:** `src/licit/core/evidence.py` (modificado)

Refactorización significativa para integrar connectors:
- `__init__` acepta `config: LicitConfig | None` — backwards compatible.
- `_run_connectors(ev)`: si config disponible y connector enabled → usa connector formal. Si no → inline.
- **Inline paths delegan a connectors**: `_collect_architect_evidence_inline` construye un `ArchitectConnector` temporal con config auto-detectada. `_collect_vigil_evidence_inline` construye un `VigilConnector` temporal. Cero duplicación de lógica de parsing.
- `connector_results` property expone los resultados de la última ejecución.
- Eliminados imports de `json` y `yaml` del módulo (ya no los necesita directamente).

#### P7.5 — CLI Mejorado

**Archivo:** `src/licit/cli.py` (modificado)

- Todos los `EvidenceCollector(root, context)` actualizados a `EvidenceCollector(root, context, config)` — connectors siempre disponibles.
- `licit connect architect`: auto-detecta `config_path`, muestra disponibilidad del connector con `available()`.
- `licit connect vigil`: detecta SARIF files del ProjectContext, muestra disponibilidad.
- `licit status`: muestra si connector está "enabled" o solo "detected". Muestra security findings si > 0.

#### P7.6 — Config de Ejemplo

**Archivo:** `.licit.example.yaml`

Configuración completa documentada con todos los campos y comentarios explicativos. Incluye connectors con `audit_log`, `sarif_path`, `sbom_path`.

#### P7.7 — Integration Tests

**Archivo:** `tests/test_integration/test_full_flow.py`

Test end-to-end con proyecto sintético (git init, commits humanos + AI, architect data, SARIF):
- `TestFullFlow` (6 tests): init → trace → report → gaps → verify → status.
- `TestConnectCommand` (2 tests): enable architect, disable vigil.
- `TestConnectorEnrichedReport` (2 tests): architect enriches report, changelog works.
- Usa `monkeypatch.chdir` para aislar cada test en su tmp_path.

### Tests Implementados

| Archivo | Tests | Cobertura |
|---------|-------|-----------|
| `test_connectors/test_architect.py` | 22 | Protocol, reports (read/empty/malformed/non-object), audit log (read/missing/malformed/empty), config (guardrails/budget/dry-run/missing/non-dict/no-guardrails), availability (3), full collect |
| `test_connectors/test_vigil.py` | 22 | Protocol, SARIF (read/auto-detect/directory/missing/malformed/non-object/runs-not-list/dedup), parsing (levels/empty/multi-run/no-location), SBOM (read/missing/malformed), availability (4) |
| `test_connectors/test_qa_edge_cases.py` | 20 | Architect (unicode/whitespace-yaml/guardrail-additive/500-lines/minimal-report/default-path/dry-run-false), Vigil (100-findings/unicode/unknown-level/no-tool/empty-dir/sbom-non-object/empty-runs), ConnectorResult (default/no-shared-list), cross-module (both-enabled/no-config-path/no-sarif), CLI (invalid-connector) |
| `test_core/test_evidence.py` (añadidos) | 9 | Connector delegation (architect-enabled/disabled-fallback/no-config-fallback), connector_results reset, ConnectorResult computed (4), SARIF non-vigil tool |
| `test_integration/test_full_flow.py` | 10 | Full flow E2E (init/trace/report/gaps/verify/status), connect (enable/disable), enriched report, changelog |
| **Total Phase 7** | **83** | |

### Resultados de QA

#### Bugs encontrados y corregidos

| # | Severidad | Descripción | Corrección |
|---|-----------|-------------|------------|
| 1 | **HIGH** | `_parse_run` en vigil.py tenía complejidad ciclomática 18 (C901). 18 branches anidados para extraer tool name, finding fields, y location. Difícil de mantener y propenso a bugs en nested dicts. | Refactorizado en 3 métodos estáticos: `_extract_tool_name()`, `_parse_finding()`, `_extract_location()`. Cada uno < 10 branches. |
| 2 | **MEDIUM** | `_read_sbom(evidence, result)` recibía `evidence` como parámetro sin usarlo (ARG002). Parámetro muerto que confunde a quien lee la API. | Removido `evidence` de la firma. Call site actualizado a `_read_sbom(result)`. |
| 3 | **MEDIUM** | `_read_audit_log`: `for line in ...: line = line.strip()` sobreescribía la variable del loop (PLW2901). Confuso, potencial fuente de bugs. | Renombrado a `raw_line`/`stripped`. |
| 4 | **MEDIUM** | `guardrail_count = X` en architect connector usaba `=` en vez de `+=`. Si dos fuentes setean guardrails, la segunda sobreescribe la primera. | Cambiado a `guardrail_count += X`. Test `test_guardrail_count_additive` verifica. |

#### Riesgos residuales

| Riesgo | Severidad | Nota |
|--------|-----------|------|
| SBOM no enriquece EvidenceBundle — read-only validation | Low | Documentado como V1; EvidenceBundle necesita campos supply-chain primero |
| `dry_run`/`rollback` defaultean a True si no se mencionan en YAML | Low | Correcto para architect (built-in feature); test `test_dry_run_explicitly_false` verifica el caso False |
| Inline path siempre corre connectors incluso si no hay datos | Low | Connectors manejan gracefully la ausencia de datos (retornan vacío) |

### Checklist de Verificación

- [x] Todos los archivos creados y funcionales
- [x] `pytest tests/ -q` — 789 tests, todos pasan
- [x] `ruff check src/licit/` — Sin errores
- [x] `mypy src/licit/ --strict` — Sin errores (50 archivos)
- [x] `python -m licit --help` — 10 comandos visibles
- [x] `licit connect architect` detecta datos y habilita connector
- [x] `licit status` muestra connector status y security findings
- [x] `licit report` genera reportes enriquecidos cuando connectors enabled
- [x] E2E manual: init → connect architect → trace → status → report → gaps → verify
- [x] Inline fallback: EvidenceCollector sin config sigue funcionando (backwards compat)
- [x] Connectors delegan correctamente sin duplicación de código
- [x] Vigil parsea SARIF de cualquier tool, no solo vigil-named
- [x] `guardrail_count` es aditivo (+=), no sobreescribe (=)
- [x] `_parse_run` refactorizado: complejidad < C901/10 por método

---

## QA V0 — Test Exhaustivo + Bug Fixes (COMPLETADA)

### Objetivo

Test exhaustivo de la CLI completa antes de release v1.0.0. Validar todos los comandos
con todas sus flags y combinaciones, en 5 proyectos simulados que representan escenarios
reales distintos, más 10 categorías de edge cases.

### Metodología

**5 proyectos de test:**

| Proyecto | Características | Commits | Agent Configs |
|----------|----------------|---------|---------------|
| `python-fastapi` | Python completo con IA, CI/CD, tests | 11 | CLAUDE.md, .cursorrules |
| `node-express` | Node.js/TypeScript con Copilot | 2 | AGENTS.md, copilot-instructions.md |
| `rust-cli` | Rust sin agent configs | 1 | (ninguno) |
| `empty-repo` | Repo mínimo (solo README) | 1 | (ninguno) |
| `architect-project` | Python con architect, vigil, SARIF | 3 | CLAUDE.md, architect config ×2 |

**142 tests ejecutados:**
- 10 comandos × flags y combinaciones por proyecto
- 10 categorías de edge cases (sin git, git sin commits, dir vacío, YAML corrupto, YAML inválido, store corrupto, permisos, stress 200 commits, configs extremas, unicode)
- Coherencia cruzada (gaps↔verify, report↔gaps, trace↔stats, status↔filesystem, fria+annex-iv mejoran verify)
- Validación de outputs (JSON parseable, HTML válido, JSONL bien formado)

### Bugs Encontrados y Corregidos

| # | Severidad | Bug | Archivo | Corrección |
|---|-----------|-----|---------|------------|
| 1 | **CRITICAL** | `trace --since` no filtraba commits (git `--since` usa committer date, no author date) | `git_analyzer.py` | Eliminado `--since` de git command. Nuevo método `_filter_since()` filtra por author date en Python con comparación timezone-aware |
| 2 | **CRITICAL** | `trace` crasheaba con traceback completo en PermissionError | `store.py` | `save()` captura `OSError` → `click.ClickException` con mensaje limpio |
| 3 | **HIGH** | Store crecía indefinidamente (append sin dedup, 10 runs × 37 records = 370 líneas) | `store.py` | `save()` ahora merge+dedup por file path (latest wins) y reescribe atómicamente. Store size proporcional a archivos únicos, no a número de runs |
| 4 | **HIGH** | Discrepancia numérica trace (59 records) vs stats (48 files) — ambos decían "files" | `cli.py` | trace ahora muestra "Analyzed N files across M records" con dedup para display |
| 5 | **MEDIUM** | `changelog --format json` guardaba JSON en `.licit/changelog.md` | `cli.py` | Extension de output ajustada al formato: `--format json` → `.changelog.json` |
| 6 | **MEDIUM** | Config `reports.output_dir` ignorada (hardcoded `.licit/reports/`) | `cli.py` | Usa `config.reports.output_dir` en vez de path hardcoded |
| 7 | **MEDIUM** | `init` sobrescribía config existente sin avisar | `cli.py` | Detecta config/directorio existente → muestra "Warning: existing configuration found — overwriting." |
| 8 | **MEDIUM** | `gaps` decía "No gaps found! All requirements met." con 0 frameworks | `cli.py` | Comprueba `frameworks_to_eval` vacío → "No frameworks enabled." (también en `report`) |
| 9 | **LOW** | Config corrupta/inválida: error solo en structlog, invisible para el usuario | `loader.py` | `_load_from_file()` ahora emite `click.echo` warning a stderr |
| 10 | **FEATURE** | `fria` requería TTY — no funcionaba en CI/CD ni con stdin piped | `fria.py` + `cli.py` | Nuevo flag `--auto`: acepta valores auto-detectados + defaults sin prompts |

### Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `src/licit/provenance/git_analyzer.py` | `_filter_since()` para filtrado por author date; import `UTC` |
| `src/licit/provenance/store.py` | `save()` merge+dedup; `_write_all()` con write mode; `OSError` handling con `click.ClickException` |
| `src/licit/cli.py` | trace display dedup; changelog ext por formato; `output_dir` from config; init warning; gaps/report empty-frameworks check; fria `--auto` flag |
| `src/licit/config/loader.py` | `click.echo` warnings en stderr para parse/validation errors |
| `src/licit/frameworks/eu_ai_act/fria.py` | `run_interactive(auto=bool)` con modo no-interactivo |
| `tests/test_provenance/test_tracker.py` | Test `--since` actualizado (filtering en Python, no git flag) |
| `tests/test_provenance/test_qa_edge_cases.py` | Test `--since` y `get_by_file` actualizados a nuevo store behavior |
| `tests/test_provenance/test_store.py` | `get_by_file` test actualizado (dedup: 1 record, not 2) |
| `tests/test_changelog/test_qa_edge_cases.py` | changelog JSON test: `.changelog.json` en vez de `.changelog.md` |

### Resultados de QA

| Categoría | Tests | OK | FAIL | WARN |
|-----------|-------|----|------|------|
| Comandos (×5 proyectos) | 90 | 90 | 0 | 0 |
| Edge cases | 13 | 13 | 0 | 0 |
| Coherencia cruzada | 8 | 8 | 0 | 0 |
| Config variations | 8 | 8 | 0 | 0 |
| CLI global | 10 | 10 | 0 | 0 |
| Output validation | 5 | 5 | 0 | 0 |
| Stress test (200 commits) | 5 | 5 | 0 | 0 |
| FRIA --auto | 3 | 3 | 0 | 0 |
| **Total** | **142** | **142** | **0** | **0** |

**Rendimiento (stress test, 200 commits):**
- `trace`: 1.7s
- `trace --stats`: 1.4s
- `report`: 2.0s
- `gaps`: 2.0s
- `verify`: 1.8s

### Checklist de Verificación

- [x] `pytest tests/ -q` — 789 tests, todos pasan
- [x] `ruff check src/licit/` — Sin errores
- [x] `trace --since` filtra correctamente por author date
- [x] `trace` no crashea con PermissionError (mensaje limpio)
- [x] Store no crece con runs repetidos (48 lines constante tras 4 runs)
- [x] `changelog --format json` guarda en `.json`, no `.md`
- [x] `reports.output_dir` de config respetado
- [x] `init` avisa al sobrescribir config existente
- [x] `gaps`/`report` muestran "No frameworks enabled" cuando corresponde
- [x] Config corrupta muestra warning visible
- [x] `fria --auto` genera archivos sin input interactivo
- [x] 5 proyectos simulados × todos los comandos × todas las flags = 0 fallos
- [x] Edge cases (sin git, sin commits, unicode, stress 200 commits) = 0 crashes
- [x] Coherencia: gaps↔verify, report↔gaps, trace↔stats, fria+annex-iv mejoran verify
