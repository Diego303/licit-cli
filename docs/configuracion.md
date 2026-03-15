# Guía de configuración

## Archivo de configuración

licit usa un archivo YAML llamado `.licit.yaml` en la raíz del proyecto. Se genera automáticamente con `licit init` pero puede editarse manualmente.

### Resolución de configuración

Cuando licit carga la configuración, sigue este orden de prioridad:

1. **Path explícito**: `licit --config /ruta/a/config.yaml <comando>`
2. **Archivo en directorio actual**: `.licit.yaml` en el cwd
3. **Defaults**: Si no existe archivo, usa valores por defecto

Si el archivo existe pero tiene errores de sintaxis YAML o validación, licit registra un warning y usa los defaults.

---

## Ejemplo completo

```yaml
# .licit.yaml — Configuración de licit
# Todos los campos son opcionales. Se muestran los valores por defecto.

provenance:
  enabled: true
  methods:
    - git-infer          # Métodos: git-infer, session-log, git-ai
  session_dirs: []       # Directorios con logs de sesión de agentes
  sign: false            # Firmar registros con HMAC-SHA256
  sign_key_path: null    # Ruta a clave de firmado
  confidence_threshold: 0.6  # Umbral mínimo para clasificar como IA
  store_path: .licit/provenance.jsonl

changelog:
  enabled: true
  watch_files:           # Archivos de config de agentes a monitorear
    - CLAUDE.md
    - .cursorrules
    - .cursor/rules
    - AGENTS.md
    - .github/copilot-instructions.md
    - .github/agents/*.md
    - .architect/config.yaml
    - architect.yaml
  output_path: .licit/changelog.md

frameworks:
  eu_ai_act: true        # Habilitar evaluación EU AI Act
  owasp_agentic: true    # Habilitar evaluación OWASP Agentic Top 10
  nist_ai_rmf: false     # Futuro (V1)
  iso_42001: false       # Futuro (V1)

connectors:
  architect:
    enabled: false
    reports_dir: .architect/reports
    audit_log: null
    config_path: null
  vigil:
    enabled: false
    sarif_path: null
    sbom_path: null

fria:
  output_path: .licit/fria-report.md
  data_path: .licit/fria-data.json
  organization: ""
  system_name: ""
  system_description: ""

annex_iv:
  output_path: .licit/annex-iv.md
  organization: ""
  product_name: ""
  product_version: ""

reports:
  output_dir: .licit/reports
  default_format: markdown   # markdown, json, html
  include_evidence: true
  include_recommendations: true
```

---

## Secciones detalladas

### provenance — Trazabilidad de código

Controla cómo licit rastrea el origen del código (IA vs humano).

| Campo | Tipo | Default | Descripción |
|---|---|---|---|
| `enabled` | bool | `true` | Habilitar trazabilidad |
| `methods` | list[str] | `["git-infer"]` | Métodos de detección |
| `session_dirs` | list[str] | `[]` | Dirs con logs de sesión |
| `sign` | bool | `false` | Firmar registros con HMAC |
| `sign_key_path` | str? | `null` | Ruta a clave de firmado |
| `confidence_threshold` | float | `0.6` | Umbral de confianza (0.0-1.0) |
| `store_path` | str | `.licit/provenance.jsonl` | Ruta al store de provenance |

**Métodos disponibles:**

- `git-infer`: **(Implementado)** Analiza heurísticas del historial git con 6 señales: patrón de autor, mensaje de commit, volumen de cambios, co-autores, patrones de archivos y hora.
- `session-log`: **(Implementado)** Lee logs de sesión de agentes IA. Actualmente soporta Claude Code (archivos JSONL en `~/.claude/projects/`). Extensible vía Protocol `SessionReader`.
- `git-ai`: Lee anotaciones de herramientas tipo git-ai (planificado).

**Ejemplo — Habilitar firmado:**
```yaml
provenance:
  sign: true
  sign_key_path: ~/.licit/signing-key
```

**Ejemplo — Múltiples métodos:**
```yaml
provenance:
  methods:
    - git-infer
    - session-log
  session_dirs:
    - ~/.claude/projects/
```

### changelog — Monitoreo de configs de agentes

> **Estado**: **Funcional** desde v0.3.0. Ejecuta con `licit changelog`.

Rastrea cambios en archivos de configuración de agentes IA a través del historial git, produciendo diffs semánticos con clasificación de severidad (MAJOR/MINOR/PATCH).

| Campo | Tipo | Default | Descripción |
|---|---|---|---|
| `enabled` | bool | `true` | Habilitar monitoreo |
| `watch_files` | list[str] | (ver ejemplo) | Archivos/globs a monitorear |
| `output_path` | str | `.licit/changelog.md` | Ruta del changelog generado |

**Archivos monitoreados por defecto:**

| Archivo | Agente |
|---|---|
| `CLAUDE.md` | Claude Code |
| `.cursorrules` | Cursor |
| `.cursor/rules` | Cursor (nuevo formato) |
| `AGENTS.md` | GitHub Agents |
| `.github/copilot-instructions.md` | GitHub Copilot |
| `.github/agents/*.md` | GitHub Agents (configs individuales) |
| `.architect/config.yaml` | Architect |
| `architect.yaml` | Architect (alternativo) |

Los patrones con `*` se resuelven usando `Path.glob()`. Los nombres exactos verifican existencia en git history.

**Pipeline de procesamiento:**
```
ConfigWatcher → Semantic Differ → ChangeClassifier → ChangelogRenderer
  (git log)     (YAML/JSON/MD)   (MAJOR/MINOR/PATCH)   (MD/JSON)
```

**Formatos de diff:** YAML y JSON producen diffs a nivel de campo (`model`, `llm.provider`). Markdown produce diffs por sección (`section:Rules`). Texto plano produce diff del contenido completo.

**Formatos de salida:** `markdown` (default) agrupa por archivo y ordena por severidad. `json` produce un objeto `{"changes": [...]}`.

**Ejemplo — Añadir archivo custom:**
```yaml
changelog:
  watch_files:
    - CLAUDE.md
    - .cursorrules
    - mi-agente-custom.yaml       # archivo adicional
    - .prompts/**/*.md             # glob recursivo
```

**Ejemplo — JSON output:**
```bash
licit changelog --format json --since 2026-01-01
```

Para documentación detallada, ver [Sistema de Changelog](changelog.md).

### frameworks — Marcos regulatorios

Controla qué marcos regulatorios se evalúan.

| Campo | Tipo | Default | Descripción |
|---|---|---|---|
| `eu_ai_act` | bool | `true` | EU AI Act (Regulamento UE 2024/1689) |
| `owasp_agentic` | bool | `true` | OWASP Agentic Top 10 |
| `nist_ai_rmf` | bool | `false` | NIST AI Risk Management Framework (futuro) |
| `iso_42001` | bool | `false` | ISO/IEC 42001 (futuro) |

**Ejemplo — Solo EU AI Act:**
```yaml
frameworks:
  eu_ai_act: true
  owasp_agentic: false
```

### connectors — Integraciones externas

> **Estado**: **Funcional** desde v0.7.0. Los conectores son formales: implementan el `Connector` Protocol, manejan errores gracefully, y reportan resultados via `ConnectorResult`.

Los conectores son **opcionales** — licit funciona completamente sin ellos. Cuando están habilitados, enriquecen el `EvidenceBundle` con datos adicionales que mejoran la evaluación de compliance.

**Auto-detección**: `licit init` detecta automáticamente la presencia de architect (`.architect/`) y vigil (`.vigil.yaml`) y habilita los conectores correspondientes.

**Fallback inline**: Cuando no hay config (`LicitConfig`) disponible, `EvidenceCollector` construye conectores temporales con rutas auto-detectadas. Esto garantiza backwards compatibility.

#### connectors.architect

Integración con Architect para leer reports de auditoría, audit logs, y configuración de guardrails.

| Campo | Tipo | Default | Descripción |
|---|---|---|---|
| `enabled` | bool | `false` | Habilitar conector (auto-enabled si `.architect/` detectado) |
| `reports_dir` | str | `.architect/reports` | Directorio de reports JSON |
| `audit_log` | str? | `null` | Ruta al log de auditoría JSONL |
| `config_path` | str? | `null` | Ruta al config YAML de architect |

**Fuentes de datos que lee:**

| Fuente | Formato | Evidencia extraída |
|---|---|---|
| Reports | JSON (`reports_dir/*.json`) | Audit trail (`has_audit_trail`, `audit_entry_count`) |
| Audit log | JSONL (`audit_log`) | Audit trail (entries adicionales al conteo) |
| Config | YAML (`config_path`) | Guardrails, quality gates, budget, dry-run, rollback |

**Campos del config YAML que extrae:**

```yaml
# .architect/config.yaml
guardrails:
  protected_files: [.env, secrets.yaml]    # → guardrail_count += N
  blocked_commands: [rm -rf]               # → guardrail_count += N
  code_rules: [no-eval]                    # → guardrail_count += N
  quality_gates: [lint, test]              # → has_quality_gates, quality_gate_count
costs:
  budget_usd: 50.0                         # → has_budget_limits
dry_run: true                              # → has_dry_run (default True si ausente)
rollback: true                             # → has_rollback (default True si ausente)
```

**Ejemplo completo:**
```yaml
connectors:
  architect:
    enabled: true
    reports_dir: .architect/reports
    config_path: .architect/config.yaml
    audit_log: .architect/audit.jsonl
```

#### connectors.vigil

Integración con Vigil y otros scanners de seguridad que producen SARIF 2.1.0.

| Campo | Tipo | Default | Descripción |
|---|---|---|---|
| `enabled` | bool | `false` | Habilitar conector (auto-enabled si `.vigil.yaml` detectado) |
| `sarif_path` | str? | `null` | Archivo SARIF o directorio con `*.sarif` |
| `sbom_path` | str? | `null` | Ruta al SBOM CycloneDX (JSON) |

**Resolución de SARIF paths:**

1. `sarif_path` explícito: si es archivo, lo lee; si es directorio, lee todos los `*.sarif`.
2. Auto-detected: archivos `.sarif` encontrados por `ProjectDetector` en el proyecto.
3. Deduplicación: si el mismo archivo aparece en ambas fuentes, se lee una sola vez.

**Mapeo de severidad SARIF:**

| Level SARIF | Clasificación licit |
|---|---|
| `error` | `security_findings_critical` |
| `warning` | `security_findings_high` |
| `note` | (contado en total, no en critical/high) |
| otro | (contado en total) |

> **Nota**: Se parsean **todos** los runs del SARIF, sin importar el nombre del tool (vigil, Semgrep, CodeQL, etc.).

**Ejemplo completo:**
```yaml
connectors:
  vigil:
    enabled: true
    sarif_path: reports/security/    # Directorio con archivos .sarif
    sbom_path: sbom.json             # CycloneDX SBOM (V1: alimentará OWASP ASI03)
```

### fria — Evaluación de Impacto en Derechos Fundamentales

Configuración para el FRIA (EU AI Act Artículo 27).

| Campo | Tipo | Default | Descripción |
|---|---|---|---|
| `output_path` | str | `.licit/fria-report.md` | Ruta del reporte |
| `data_path` | str | `.licit/fria-data.json` | Ruta de datos raw |
| `organization` | str | `""` | Nombre de la organización |
| `system_name` | str | `""` | Nombre del sistema |
| `system_description` | str | `""` | Descripción del sistema |

### annex_iv — Documentación Técnica Anexo IV

| Campo | Tipo | Default | Descripción |
|---|---|---|---|
| `output_path` | str | `.licit/annex-iv.md` | Ruta del documento |
| `organization` | str | `""` | Nombre de la organización |
| `product_name` | str | `""` | Nombre del producto |
| `product_version` | str | `""` | Versión del producto |

### reports — Generación de reportes

| Campo | Tipo | Default | Descripción |
|---|---|---|---|
| `output_dir` | str | `.licit/reports` | Directorio de salida |
| `default_format` | str | `markdown` | Formato: markdown, json, html |
| `include_evidence` | bool | `true` | Incluir evidencia en reportes |
| `include_recommendations` | bool | `true` | Incluir recomendaciones |

---

## Directorio de datos (.licit/)

licit almacena toda su data interna en el directorio `.licit/` dentro de la raíz del proyecto.

```
.licit/
├── .signing-key        # Clave HMAC-SHA256 (auto-generada si sign=true)
├── provenance.jsonl    # Store de trazabilidad (JSONL append-only)
├── changelog.md        # Changelog de configs de agentes
├── fria-data.json      # Datos raw del FRIA
├── fria-report.md      # Reporte FRIA legible
├── annex-iv.md         # Documentación técnica Anexo IV
└── reports/            # Reportes generados
    ├── provenance.md          # Reporte de proveniencia
    ├── compliance-report.md
    ├── compliance-report.json
    └── compliance-report.html
```

**Recomendación de `.gitignore`:**
```gitignore
# licit — datos internos (pueden contener información sensible)
.licit/provenance.jsonl
.licit/fria-data.json

# licit — reportes generados (commit si se desea)
# .licit/reports/
```

Se recomienda hacer commit de `.licit.yaml` y los reportes generados, pero **no** del store de provenance ni los datos raw del FRIA, ya que pueden contener información sensible del equipo.

---

## Uso programático

La configuración puede cargarse y manipularse desde Python:

```python
from licit.config.loader import load_config, save_config

# Cargar
config = load_config()  # Busca .licit.yaml automáticamente
config = load_config("/ruta/explícita/.licit.yaml")

# Modificar
config.frameworks.owasp_agentic = False
config.connectors.architect.enabled = True

# Guardar
save_config(config)  # Guarda en .licit.yaml
save_config(config, "/otra/ruta/config.yaml")
```
