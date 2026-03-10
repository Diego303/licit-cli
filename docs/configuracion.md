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

- `git-infer`: Analiza heurísticas del historial git (patrones de autor, mensaje de commit, volumen de cambios).
- `session-log`: Lee logs de sesión de agentes IA (Claude Code, Cursor, etc.).
- `git-ai`: Lee anotaciones de herramientas tipo git-ai.

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

Rastrea cambios en archivos de configuración de agentes IA a través del historial git.

| Campo | Tipo | Default | Descripción |
|---|---|---|---|
| `enabled` | bool | `true` | Habilitar monitoreo |
| `watch_files` | list[str] | (ver ejemplo) | Archivos a monitorear |
| `output_path` | str | `.licit/changelog.md` | Ruta del changelog |

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

**Ejemplo — Añadir archivo custom:**
```yaml
changelog:
  watch_files:
    - CLAUDE.md
    - .cursorrules
    - mi-agente-custom.yaml  # archivo adicional
```

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

#### connectors.architect

Integración con Architect para leer reports de auditoría y configuración de guardrails.

| Campo | Tipo | Default | Descripción |
|---|---|---|---|
| `enabled` | bool | `false` | Habilitar conector |
| `reports_dir` | str | `.architect/reports` | Dir de reports |
| `audit_log` | str? | `null` | Ruta al log de auditoría JSONL |
| `config_path` | str? | `null` | Ruta al config de architect |

**Ejemplo:**
```yaml
connectors:
  architect:
    enabled: true
    config_path: .architect/config.yaml
    audit_log: .architect/audit.jsonl
```

#### connectors.vigil

Integración con Vigil para leer hallazgos de seguridad en formato SARIF.

| Campo | Tipo | Default | Descripción |
|---|---|---|---|
| `enabled` | bool | `false` | Habilitar conector |
| `sarif_path` | str? | `null` | Ruta al archivo SARIF |
| `sbom_path` | str? | `null` | Ruta al SBOM |

**Ejemplo:**
```yaml
connectors:
  vigil:
    enabled: true
    sarif_path: reports/vigil-results.sarif
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
├── provenance.jsonl    # Store de trazabilidad (JSONL)
├── changelog.md        # Changelog de configs de agentes
├── fria-data.json      # Datos raw del FRIA
├── fria-report.md      # Reporte FRIA legible
├── annex-iv.md         # Documentación técnica Anexo IV
└── reports/            # Reportes generados
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
