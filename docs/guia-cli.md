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
# licit, version 0.1.0

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

Project: mi-proyecto-fastapi
  Root: /home/user/mi-proyecto-fastapi
  Languages: python
  Frameworks: fastapi
  Git: 142 commits, 3 contributors

Config: .licit.yaml (loaded)

Frameworks:
  EU AI Act: enabled
  OWASP Agentic: enabled

Data sources:
  Provenance: not collected
  FRIA: not found
  Annex IV: not found
  Changelog: not found

Connectors:
  architect: disabled
  vigil: disabled

Agent configs:
  CLAUDE.md (claude-code)
  .cursorrules (cursor)
```

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

**Ejemplo:**
```bash
$ licit connect architect
# Habilita el conector de architect

$ licit connect vigil --enable
# Habilita el conector de vigil

$ licit connect architect --disable
# Deshabilita el conector de architect
```

---

### `licit trace`

Rastrea la proveniencia del código — identifica qué fue escrito por IA y qué por humanos.

> **Estado**: Registrado en CLI. Funcional a partir de Fase 2.

```bash
licit trace [--since DATE|TAG] [--report] [--stats]
```

**Opciones:**

| Opción | Descripción |
|---|---|
| `--since` | Analiza commits desde una fecha (YYYY-MM-DD) o tag de git |
| `--report` | Genera archivo de reporte de proveniencia |
| `--stats` | Muestra estadísticas en terminal |

**Ejemplo futuro:**
```bash
$ licit trace --since 2026-01-01 --stats

Provenance Analysis (since 2026-01-01):
  Total files analyzed: 87
  AI-authored: 34 (39.1%)
  Human-authored: 41 (47.1%)
  Mixed: 12 (13.8%)
  Confidence: 0.82 avg
```

---

### `licit changelog`

Genera un changelog de cambios en configuraciones de agentes IA.

> **Estado**: Registrado en CLI. Funcional a partir de Fase 3.

```bash
licit changelog [--since DATE|TAG] [--format {markdown|json}]
```

**Opciones:**

| Opción | Default | Descripción |
|---|---|---|
| `--since` | (todos) | Cambios desde fecha o tag |
| `--format` | `markdown` | Formato de salida |

**Archivos monitoreados:**
- `CLAUDE.md`
- `.cursorrules`, `.cursor/rules`
- `AGENTS.md`
- `.github/copilot-instructions.md`
- `.github/agents/*.md`
- `.architect/config.yaml`, `architect.yaml`

---

### `licit fria`

Completa la Evaluación de Impacto en Derechos Fundamentales (EU AI Act Artículo 27).

> **Estado**: Registrado en CLI. Funcional a partir de Fase 4.

```bash
licit fria [--update]
```

**Opciones:**

| Opción | Descripción |
|---|---|
| `--update` | Actualiza un FRIA existente en lugar de crear uno nuevo |

**Archivos generados:**
- `.licit/fria-data.json` — Datos raw de la evaluación
- `.licit/fria-report.md` — Reporte legible del FRIA

---

### `licit annex-iv`

Genera la Documentación Técnica del Anexo IV (EU AI Act).

> **Estado**: Registrado en CLI. Funcional a partir de Fase 4.

```bash
licit annex-iv [--organization NOMBRE] [--product NOMBRE]
```

**Opciones:**

| Opción | Descripción |
|---|---|
| `--organization` | Nombre de la organización |
| `--product` | Nombre del producto |

**Archivo generado:**
- `.licit/annex-iv.md`

---

### `licit report`

Genera un reporte de compliance unificado.

> **Estado**: Registrado en CLI. Funcional a partir de Fase 6.

```bash
licit report [--framework {eu-ai-act|owasp|all}] [--format {markdown|json|html}] [--output PATH]
```

**Opciones:**

| Opción | Default | Descripción |
|---|---|---|
| `--framework` | `all` | Marco a evaluar |
| `--format` | `markdown` | Formato de salida |
| `-o`, `--output` | `.licit/reports/compliance-report.{ext}` | Ruta del archivo de salida |

---

### `licit gaps`

Identifica brechas de compliance con recomendaciones accionables.

> **Estado**: Registrado en CLI. Funcional a partir de Fase 6.

```bash
licit gaps [--framework {eu-ai-act|owasp|all}]
```

**Opciones:**

| Opción | Default | Descripción |
|---|---|---|
| `--framework` | `all` | Marco a analizar |

**Ejemplo futuro:**
```bash
$ licit gaps --framework eu-ai-act

EU AI Act Compliance Gaps:

[HIGH] ART-9-1: Risk Management System
  Gap: No FRIA document found
  Action: Run 'licit fria' to complete the assessment
  Effort: medium

[MEDIUM] ART-13-1: Transparency
  Gap: No provenance tracking configured
  Action: Run 'licit trace' to analyze code provenance
  Effort: low
```

---

### `licit verify`

Verifica compliance y devuelve código de salida para CI/CD.

> **Estado**: Registrado en CLI. Funcional a partir de Fase 6.

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
| `trace` | 2 | Skeleton | Trazabilidad de proveniencia |
| `changelog` | 3 | Skeleton | Changelog de configs de agentes |
| `fria` | 4 | Skeleton | FRIA (EU AI Act Art. 27) |
| `annex-iv` | 4 | Skeleton | Documentación técnica Anexo IV |
| `report` | 6 | Skeleton | Reporte unificado de compliance |
| `gaps` | 6 | Skeleton | Brechas de compliance |
| `verify` | 6 | Skeleton | Gate de CI/CD |
