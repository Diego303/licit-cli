# Guía de CLI

## Instalación

```bash
pip install licit-ai-cli
```

O desde el código fuente:

```bash
git clone https://github.com/Diego303/licit-cli.git
cd licit-cli
pip install -e ".[dev]"
```

## Invocación

```bash
# Como comando instalado
licit [opciones] <comando> [argumentos]

# Como módulo Python
python -m licit [opciones] <comando> [argumentos]
```

## Opciones globales

| Opción | Descripción |
|---|---|
| `--version` | Muestra la versión de licit |
| `--config PATH` | Ruta a un archivo `.licit.yaml` específico |
| `-v`, `--verbose` | Activa logging detallado (nivel DEBUG) |
| `--help` | Muestra la ayuda |

```bash
licit --version
# licit, version 1.0.0

licit --verbose status
# Muestra logs de debug durante la ejecución
```

---

## Comandos

### `licit init`

Inicializa licit en el proyecto actual. Detecta automáticamente las características del proyecto y genera la configuración.

```bash
licit init [--framework {eu-ai-act|owasp|all}]
```

**Opciones:**

| Opción | Default | Descripción |
|---|---|---|
| `--framework` | `all` | Marco regulatorio a habilitar |

**Qué hace:**
1. Ejecuta `ProjectDetector` para detectar lenguajes, frameworks, CI/CD, agentes IA, etc.
2. Genera `.licit.yaml` con configuración adaptada al proyecto.
3. Crea el directorio `.licit/` para datos internos.
4. Si detecta architect o vigil, habilita sus conectores automáticamente.

**Ejemplo:**
```bash
$ cd mi-proyecto-fastapi/
$ licit init

Initialized licit in mi-proyecto-fastapi
  Languages: python
  Frameworks: fastapi
  Agent configs: CLAUDE.md
  CI/CD: github-actions
  Config saved to .licit.yaml
```

**Ejemplo con framework específico:**
```bash
$ licit init --framework eu-ai-act
# Solo habilita EU AI Act, desactiva OWASP
```

---

### `licit status`

Muestra el estado actual de licit y las fuentes de datos conectadas.

```bash
licit status
```

**Qué muestra:**
- Información del proyecto (nombre, lenguajes, frameworks)
- Estado de la configuración
- Frameworks habilitados (EU AI Act, OWASP)
- Fuentes de datos detectadas (provenance, FRIA, changelog, etc.)
- Conectores configurados (architect, vigil)
- Configuraciones de agentes IA encontradas

**Ejemplo:**
```bash
$ licit status

  licit Status
  ────────────────────────────────────────
  Project: mi-proyecto-fastapi
  Config: .licit.yaml

  Frameworks:
    [x] EU AI Act
    [x] OWASP Agentic Top 10
    [ ] NIST AI RMF (V1)
    [ ] ISO 42001 (V1)

  Data Sources:
    [x] Git history (142 commits)
    [x] Provenance tracking
    [ ] Config changelog
    [ ] FRIA document
    [ ] Annex IV documentation

  Connectors:
    [x] architect (.architect/config.yaml, enabled)
    [x] vigil (.vigil.yaml, enabled)
    Security findings: 3 total (1 critical, 1 high)

  Agent Configs (2):
    - CLAUDE.md (claude-code)
    - .cursorrules (cursor)
```

El comando `status` ahora muestra:
- Estado de connectors como "enabled" o "detected"
- Conteo de security findings cuando hay hallazgos SARIF

---

### `licit connect`

Configura conectores opcionales para integrar fuentes de datos externas.

```bash
licit connect {architect|vigil} [--enable|--disable]
```

**Argumentos:**

| Argumento | Descripción |
|---|---|
| `architect` | Conector para Architect (reports y audit logs) |
| `vigil` | Conector para Vigil (hallazgos SARIF de seguridad) |

**Opciones:**

| Opción | Default | Descripción |
|---|---|---|
| `--enable` | (por defecto) | Habilita el conector |
| `--disable` | | Deshabilita el conector |

**Qué hace:**
1. Habilita o deshabilita el conector en `.licit.yaml`.
2. Al habilitar, auto-detecta rutas de configuración si no están configuradas.
3. Verifica la disponibilidad de datos en disco con `available()`.
4. Muestra feedback sobre si se encontraron datos del conector.

**Ejemplo:**
```bash
$ licit connect architect
  architect data found at: .architect/reports
  Connector 'architect' enabled.

$ licit connect vigil --enable
  vigil data found
  Connector 'vigil' enabled.

$ licit connect architect --disable
  Connector 'architect' disabled.
```

**Datos que enriquecen los conectores:**

| Conector | Fuentes de datos | Evidencia aportada |
|---|---|---|
| **architect** | Reports JSON, audit JSONL, config YAML | Audit trail, guardrails, quality gates, budget, dry-run, rollback |
| **vigil** | SARIF 2.1.0, SBOM CycloneDX | Security findings (critical/high/medium/low) |

---

### `licit trace`

Rastrea la proveniencia del código — identifica qué fue escrito por IA y qué por humanos.

> **Estado**: **Funcional** (Fase 2 completada).

```bash
licit trace [--since DATE|TAG] [--report] [--stats]
```

**Opciones:**

| Opción | Descripción |
|---|---|
| `--since` | Analiza commits desde una fecha (YYYY-MM-DD). Filtra por author date |
| `--report` | Genera archivo de reporte de proveniencia en `.licit/reports/provenance.md` |
| `--stats` | Muestra estadísticas en terminal |

**Qué hace:**
1. Ejecuta `GitAnalyzer` para analizar commits con 6 heurísticas (autor, mensaje, volumen, co-autores, patrones de archivos, hora).
2. Opcionalmente lee logs de sesión de agentes (Claude Code).
3. Clasifica cada archivo como `ai` (score >= 0.7), `mixed` (>= 0.5) o `human` (< 0.5).
4. Almacena resultados en `.licit/provenance.jsonl` (merge + deduplicación por archivo).
5. Si `sign: true`, firma cada registro con HMAC-SHA256.

**Ejemplo:**
```bash
$ licit trace --since 2026-01-01

  Analyzing git history for AI provenance...
  Analyzed 45 files across 52 records
  AI-generated: 18 files
  Human-written: 22 files

$ licit trace --stats

  Provenance Statistics
  ────────────────────────────────────────
  Total files tracked: 45
  AI-generated:        18 (40.0%)
  Human-written:       22
  Mixed:               5
```

**Ejemplo con reporte:**
```bash
$ licit trace --report
# Genera .licit/reports/provenance.md con tabla detallada por archivo
```

**Heurísticas utilizadas:**

| # | Heurística | Peso | Qué detecta |
|---|---|---|---|
| H1 | Author pattern | 3.0 | Nombres de autor AI (claude, copilot, cursor, bot, etc.) |
| H2 | Message pattern | 1.5 | Patrones de commit (conventional commits, "implement", `[ai]`) |
| H3 | Bulk changes | 2.0 | Cambios masivos (>20 archivos + >500 líneas) |
| H4 | Co-author | 3.0 | `Co-authored-by:` con keywords AI |
| H5 | File patterns | 1.0 | Todos los archivos son test files |
| H6 | Time pattern | 0.5 | Commits entre 1am-5am |

Solo las heurísticas que producen señal (score > 0) contribuyen al promedio ponderado.

---

### `licit changelog`

Genera un changelog de cambios en configuraciones de agentes IA con diffing semántico y clasificación de severidad.

> **Estado**: **Funcional** (Fase 3 completada).

```bash
licit changelog [--since DATE|TAG] [--format {markdown|json}]
```

**Opciones:**

| Opción | Default | Descripción |
|---|---|---|
| `--since` | (todos) | Cambios desde fecha o tag |
| `--format` | `markdown` | Formato de salida: `markdown` o `json` |

**Qué hace:**
1. Ejecuta `ConfigWatcher` para recuperar el historial git de los archivos monitoreados.
2. Aplica `diff_configs()` (differ semántico) entre versiones consecutivas de cada archivo.
3. Clasifica cada cambio con `ChangeClassifier` (MAJOR/MINOR/PATCH).
4. Renderiza el changelog con `ChangelogRenderer` (Markdown o JSON).
5. Muestra el output en terminal y lo guarda en `output_path`.

**Archivos monitoreados (por defecto):**
- `CLAUDE.md`, `.cursorrules`, `.cursor/rules`
- `AGENTS.md`, `.github/copilot-instructions.md`, `.github/agents/*.md`
- `.architect/config.yaml`, `architect.yaml`

**Ejemplo:**
```bash
$ licit changelog

# Agent Config Changelog

> 3 change(s) detected across 2 file(s): **1** major, **1** minor, **1** patch

## .architect/config.yaml

- **[MAJOR]** Changed: model from claude-sonnet-4 to claude-opus-4 (`a1b2c3d4`) — 2026-03-12
- **[PATCH]** Changed: budget.max_cost_usd from 5.0 to 10.0 (`a1b2c3d4`) — 2026-03-12

## CLAUDE.md

- **[MINOR]** Changed: section:Rules from 5 lines to 8 lines (+3/-0) (`e5f6g7h8`) — 2026-03-11

  Changelog saved to .licit/changelog.md
```

**Ejemplo JSON:**
```bash
$ licit changelog --format json --since 2026-03-01
# Genera JSON con array "changes" y guarda en .licit/changelog.json
```

**Clasificación de severidad:**

| Severidad | Trigger | Ejemplos |
|---|---|---|
| **MAJOR** | Cambio de modelo/provider, o eliminación de campo MINOR | `model: gpt-4` → `gpt-5`, borrar `guardrails` |
| **MINOR** | Cambio de prompt, guardrails, tools, reglas, secciones Markdown | Editar `system_prompt`, añadir `blocked_commands` |
| **PATCH** | Todo lo demás | Ajuste de parámetros, formatting |

**Formatos de diff soportados:**

| Formato | Extensiones | Estrategia |
|---|---|---|
| YAML | `.yaml`, `.yml` | Diff recursivo de key-value |
| JSON | `.json` | Diff recursivo de key-value |
| Markdown | `.md` | Diff por secciones (headings) |
| Texto plano | Otros | Diff de contenido completo |

Para documentación detallada del sistema de changelog, ver [Changelog](../docs/changelog.md).

---

### `licit fria`

Completa la Evaluación de Impacto en Derechos Fundamentales (EU AI Act Artículo 27).

> **Estado**: **Funcional** (Fase 4 completada).

```bash
licit fria [--update] [--auto]
```

**Opciones:**

| Opción | Descripción |
|---|---|
| `--update` | Actualiza un FRIA existente en lugar de crear uno nuevo |
| `--auto` | Modo no-interactivo: acepta valores auto-detectados y defaults sin prompts (ideal para CI/CD) |

**Qué hace:**
1. Detecta el proyecto y recopila evidencia disponible.
2. Ejecuta un cuestionario interactivo de 5 pasos (16 preguntas). Con `--auto`, acepta automáticamente todos los valores detectados y usa la primera opción como default para preguntas sin auto-detección.
3. Auto-detecta respuestas donde es posible (8 campos: system_purpose, ai_technology, models_used, human_review, guardrails, security_scanning, testing, audit_trail).
4. Guarda datos en `.licit/fria-data.json` y genera reporte en `.licit/fria-report.md`.

**5 pasos del cuestionario:**

| Paso | Título | Preguntas |
|---|---|---|
| 1 | System Description | Propósito, tecnología AI, modelos, alcance, revisión humana |
| 2 | Fundamental Rights Identification | Datos personales, empleo, seguridad, discriminación |
| 3 | Impact Assessment | Nivel de riesgo, impacto máximo, velocidad de detección |
| 4 | Mitigation Measures | Guardrails, scanning, testing, audit trail, medidas adicionales |
| 5 | Monitoring & Review | Frecuencia de revisión, responsable, proceso de incidentes |

**Auto-detección:** Para campos marcados con `auto_detect`, licit intenta inferir la respuesta desde la configuración del proyecto. Si lo consigue, muestra el valor detectado y pregunta si aceptarlo.

**Archivos generados:**
- `.licit/fria-data.json` — Datos raw de la evaluación (JSON, reutilizable con `--update`)
- `.licit/fria-report.md` — Reporte Markdown legible del FRIA

**Ejemplo:**
```bash
$ licit fria

============================================================
  FUNDAMENTAL RIGHTS IMPACT ASSESSMENT (FRIA)
  EU AI Act -- Article 27
============================================================

──────────────────────────────────────────────────
  Step 1: System Description
──────────────────────────────────────────────────

  [1.1] What is the primary purpose of this AI system?
  -> Auto-detected: AI-assisted code development using claude-code
    Accept this value? [Y/n]:
```

---

### `licit annex-iv`

Genera la Documentación Técnica del Anexo IV (EU AI Act).

> **Estado**: **Funcional** (Fase 4 completada).

```bash
licit annex-iv [--organization NOMBRE] [--product NOMBRE]
```

**Opciones:**

| Opción | Descripción |
|---|---|
| `--organization` | Nombre de la organización (default: nombre del proyecto) |
| `--product` | Nombre del producto (default: nombre del proyecto) |

**Qué hace:**
1. Detecta el proyecto y recopila toda la evidencia disponible.
2. Auto-puebla un documento Annex IV con 6 secciones desde los metadatos del proyecto.
3. Genera recomendaciones para secciones con evidencia faltante.
4. Escribe el resultado en `.licit/annex-iv.md`.

**6 secciones auto-generadas:**

| Sección | Contenido |
|---|---|
| 1. General Description | Propósito, componentes AI, lenguajes, frameworks |
| 2. Development Process | Control de versiones, provenance AI, configs de agentes |
| 3. Monitoring & Control | CI/CD, audit trail, changelog |
| 4. Risk Management | Guardrails, quality gates, budget, oversight, FRIA |
| 5. Testing & Validation | Framework de tests, herramientas de seguridad |
| 6. Changes & Lifecycle | Resumen de mecanismos de tracking |

**Ejemplo:**
```bash
$ licit annex-iv --organization "ACME Corp" --product "WebApp"

  Annex IV documentation saved to: .licit/annex-iv.md
```

**Archivo generado:**
- `.licit/annex-iv.md` — Documentación técnica completa en Markdown

---

### `licit report`

Genera un reporte de compliance unificado.

> **Estado**: **Funcional** (Fase 6). Evalúa EU AI Act + OWASP Agentic Top 10. Soporta Markdown, JSON y HTML.

```bash
licit report [--framework {eu-ai-act|owasp|all}] [--format {markdown|json|html}] [--output PATH]
```

**Opciones:**

| Opción | Default | Descripción |
|---|---|---|
| `--framework` | `all` | Marco a evaluar |
| `--format` | `markdown` | Formato de salida |
| `-o`, `--output` | `.licit/reports/compliance-report.{ext}` | Ruta del archivo de salida |

**Ejemplo:**
```bash
$ licit report --framework eu-ai-act

  Compliance Summary
  ─────────────────────────────────────────────
  Project: my-app
  Generated: 2026-03-15 12:00 UTC

  eu-ai-act (2024/1689)
    [##..................] 9.1%
    1 compliant | 4 partial | 6 non-compliant

  ─────────────────────────────────────────────
  Overall: [##..................] 9.1%
  1/11 controls compliant

  Report saved to: .licit/reports/compliance-report.md
```

**Formatos de salida:**

| Formato | Descripción |
|---|---|
| `markdown` | Tablas de resumen + detalle por requisito con iconos `[PASS]`/`[FAIL]`/`[PARTIAL]` |
| `json` | JSON estructurado con `overall`, `frameworks[]`, `results[]` |
| `html` | HTML auto-contenido (sin dependencias externas), badges de color, responsive |

**Archivos generados:**
- `.licit/reports/compliance-report.md` (o `.json`/`.html` según `--format`)

---

### `licit gaps`

Identifica brechas de compliance con recomendaciones accionables.

> **Estado**: **Funcional** (Fase 6). Muestra gaps con herramientas sugeridas y nivel de esfuerzo.

```bash
licit gaps [--framework {eu-ai-act|owasp|all}]
```

**Opciones:**

| Opción | Default | Descripción |
|---|---|---|
| `--framework` | `all` | Marco a analizar |

**Ejemplo:**
```bash
$ licit gaps --framework eu-ai-act

  10 compliance gap(s) found:

  1. [X] [ART-27-1] Fundamental Rights Impact Assessment (FRIA)
     Missing: Before putting an AI system into use, deployers shall
     carry out an assessment of the impact on fundamental rights.
     -> Run: licit fria -- to complete the FRIA
     Tools: licit fria

  2. [!] [ART-12-1] Record Keeping — Automatic Logging
     Incomplete: AI systems shall be designed with capabilities enabling
     automatic recording of events (logs) over the lifetime.
     -> Enable structured audit trail (architect reports or manual logging)
     Tools: licit trace, architect (audit log)
```

Los gaps se ordenan por severidad (`[X]` non-compliant antes que `[!]` partial) y cada uno incluye descripción, recomendación, y herramientas sugeridas.

---

### `licit verify`

Verifica compliance y devuelve código de salida para CI/CD.

> **Estado**: **Funcional** (Fases 4-5). Evalúa EU AI Act (11 artículos) y OWASP Agentic Top 10 (10 riesgos).

```bash
licit verify [--framework {eu-ai-act|owasp|all}]
```

**Códigos de salida:**

| Código | Significado |
|---|---|
| `0` | COMPLIANT — Todos los requisitos críticos cumplidos |
| `1` | NON_COMPLIANT — Algún requisito crítico no cumplido |
| `2` | PARTIAL — Algún requisito parcialmente cumplido |

**Uso en CI/CD (GitHub Actions):**
```yaml
- name: Compliance check
  run: licit verify
  # El pipeline falla si exit code != 0
```

---

## Tabla resumen de comandos

| Comando | Fase | Estado | Descripción corta |
|---|---|---|---|
| `init` | 1 | Funcional | Inicializa licit en el proyecto |
| `status` | 1 | Funcional | Muestra estado y fuentes conectadas |
| `connect` | 1 | Funcional | Configura conectores |
| `trace` | 2 | **Funcional** | Trazabilidad de proveniencia |
| `changelog` | 3 | **Funcional** | Changelog de configs de agentes |
| `fria` | 4 | **Funcional** | FRIA (EU AI Act Art. 27) |
| `annex-iv` | 4 | **Funcional** | Documentación técnica Anexo IV |
| `report` | 6 | **Funcional** | Reporte unificado (MD/JSON/HTML) |
| `gaps` | 6 | **Funcional** | Brechas con recomendaciones |
| `verify` | 4-6 | **Funcional (EU AI Act + OWASP)** | Gate de CI/CD |
