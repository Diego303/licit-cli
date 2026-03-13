# Sistema de Changelog

Sistema de monitoreo de cambios en archivos de configuración de agentes IA, con diffing semántico, clasificación de severidad y rendering en Markdown/JSON.

> **Estado**: **Funcional** desde v0.3.0 (Fase 3 completada).

---

## Visión general

El sistema de changelog responde a la pregunta: **¿qué cambió en la configuración de los agentes IA?** Monitorea archivos como `CLAUDE.md`, `.cursorrules`, `AGENTS.md` y configs YAML/JSON a través del historial de git, produciendo diffs semánticos con clasificación de severidad.

```bash
licit changelog
```

```markdown
# Agent Config Changelog

> 3 change(s) detected across 2 file(s): **1** major, **1** minor, **1** patch

## .architect/config.yaml

- **[MAJOR]** Changed: model from claude-sonnet-4 to claude-opus-4 (`a1b2c3d4`) — 2026-03-12
- **[PATCH]** Changed: budget.max_cost_usd from 5.0 to 10.0 (`a1b2c3d4`) — 2026-03-12

## CLAUDE.md

- **[MINOR]** Changed: section:Rules from 5 lines to 8 lines (+3/-0) (`e5f6g7h8`) — 2026-03-11
```

---

## Arquitectura

El sistema se compone de 4 módulos en `src/licit/changelog/`:

```
changelog/
├── watcher.py       # Monitoreo de archivos via git history
├── differ.py        # Diffing semántico por formato de archivo
├── classifier.py    # Clasificación de severidad (MAJOR/MINOR/PATCH)
└── renderer.py      # Rendering en Markdown o JSON
```

### Pipeline

```
ConfigWatcher ──→ Semantic Differ ──→ Change Classifier ──→ Renderer
  (git log)       (YAML/JSON/MD)     (MAJOR/MINOR/PATCH)   (MD/JSON)
       │                │                     │                  │
  ConfigSnapshot[]   FieldDiff[]        ConfigChange[]      String output
```

---

## Config Watcher

`ConfigWatcher` monitorea archivos de configuración de agentes IA a través del historial de git.

### ConfigSnapshot

```python
@dataclass
class ConfigSnapshot:
    path: str          # Ruta relativa del archivo
    content: str       # Contenido del archivo en ese commit
    commit_sha: str    # Hash SHA del commit
    timestamp: datetime # Fecha del commit (timezone-aware)
    author: str        # Autor del commit
```

### Uso

```python
from licit.changelog.watcher import ConfigWatcher

watcher = ConfigWatcher(root_dir="/path/to/project", watch_patterns=["CLAUDE.md", "*.yaml"])

# Archivos que existen actualmente en disco
files = watcher.get_watched_files()

# Historial de cambios de todos los archivos watched
history = watcher.get_config_history()
# → {"CLAUDE.md": [ConfigSnapshot, ...], "config.yaml": [...]}

# Historial desde una fecha
history = watcher.get_config_history(since="2026-01-01")
```

### Resolución de patrones

Los `watch_patterns` se resuelven de dos formas:

| Tipo | Ejemplo | Resolución |
|---|---|---|
| Nombre exacto | `CLAUDE.md` | Verifica existencia en git history (`git log --oneline -1`) |
| Glob | `.prompts/**/*.md` | Resuelve con `Path.glob()` y filtra archivos existentes |

### Protecciones

- **Size guard**: `_MAX_CONTENT_BYTES = 1_048_576` (1 MB) en `git show`. Archivos más grandes se descartan con log warning.
- **Timeouts**: 10s para verificación de existencia, 30s para `git log`.
- **Deduplicación**: Un `seen: set[str]` evita procesar el mismo archivo dos veces cuando múltiples patrones lo matchean.
- **Deleted files**: Si el archivo fue eliminado en un commit, se registra como contenido vacío.

---

## Semantic Differ

`diff_configs()` produce diffs semánticos según el formato del archivo.

### FieldDiff

```python
@dataclass
class FieldDiff:
    field_path: str           # "model", "llm.provider", "section:Rules"
    old_value: str | None     # Valor anterior (None si es adición)
    new_value: str | None     # Valor nuevo (None si es eliminación)
    is_addition: bool = False # Campo nuevo
    is_removal: bool = False  # Campo eliminado
```

### Formatos soportados

| Formato | Extensiones | Estrategia |
|---|---|---|
| YAML | `.yaml`, `.yml` | Dict recursivo key-value con `_diff_dicts()` |
| JSON | `.json` | Dict recursivo key-value con `_diff_dicts()` |
| Markdown | `.md` | Secciones por headings con `_parse_md_sections()` |
| Texto plano | Otros | Diff de contenido completo |

### YAML / JSON

Parsea ambas versiones, luego diff recursivo de diccionarios:

```python
diffs = diff_configs("model: gpt-4\ntemp: 0.7\n", "model: gpt-5\ntemp: 0.7\n", "config.yaml")
# → [FieldDiff(field_path="model", old_value="gpt-4", new_value="gpt-5")]
```

**Dicts anidados** se recurren:

```python
diffs = diff_configs("llm:\n  model: gpt-4\n", "llm:\n  model: gpt-5\n", "config.yaml")
# → [FieldDiff(field_path="llm.model", old_value="gpt-4", new_value="gpt-5")]
```

**Roots no-dict** (listas, escalares) se wrappean como `{"(root)": data}` en vez de descartarse.

**Errores de parseo** producen `FieldDiff(field_path="(parse-error)")` sin crashear.

### Markdown

Parsea headings ATX (`#`, `##`, `###`, etc.) y produce diffs por sección:

```python
old = "# Rules\n\nOriginal rules\n"
new = "# Rules\n\nModified rules\n\n## New Section\n\nContent\n"
diffs = diff_configs(old, new, "CLAUDE.md")
# → [FieldDiff(field_path="section:Rules", ...), FieldDiff(field_path="section:New Section", ...)]
```

**Fenced code blocks**: `_parse_md_sections()` trackea bloques ``` para no interpretar headings dentro de código.

**Sin headings**: Si el markdown no tiene headings, se cae a diff de contenido completo como `(content)`.

### Texto plano

Para archivos como `.cursorrules`:

```python
diffs = diff_configs("line1\nline2\n", "line1\nline3\n", ".cursorrules")
# → [FieldDiff(field_path="(content)", old_value="2 lines", new_value="2 lines (+1/-1)")]
```

---

## Change Classifier

`ChangeClassifier` asigna severidad a cada `FieldDiff` y produce `ConfigChange`.

### Reglas de severidad

| Severidad | Trigger | Ejemplos |
|---|---|---|
| **MAJOR** | Campo en `_MAJOR_FIELDS` | `model`, `llm.model`, `provider`, `backend` |
| **MINOR** | Campo en `_MINOR_FIELDS` | `prompt`, `guardrails`, `tools`, `rules`, `blocked_commands` |
| **MAJOR** (escalación) | Eliminación de campo MINOR | Borrar `guardrails`, borrar `protected_files` |
| **MINOR** | Cambio en sección Markdown | `section:Rules`, `section:Instructions` |
| **PATCH** | Todo lo demás | Tweaks de parámetros, formatting, comentarios |

### Matching por segmentos

`_field_matches()` compara los últimos N segmentos del campo contra el patrón:

```python
_field_matches("llm.model", "model")       # True  — último segmento = "model"
_field_matches("model", "model")            # True  — segmento único coincide
_field_matches("model_config", "model")     # False — "model_config" ≠ "model"
_field_matches("section:model", "model")    # False — "section:model" ≠ "model"
_field_matches("llm.model", "llm.model")    # True  — últimos 2 segmentos coinciden
```

Esto previene falsos positivos donde campos como `model_config` se clasificaban erróneamente como MAJOR.

### Uso

```python
from licit.changelog.classifier import ChangeClassifier

classifier = ChangeClassifier()
changes = classifier.classify_changes(
    old_content="model: gpt-4\n",
    new_content="model: gpt-5\n",
    file_path="config.yaml",
    commit_sha="abc1234",
    timestamp=datetime(2026, 3, 10, tzinfo=UTC),
)
# → [ConfigChange(severity=MAJOR, description="Changed: model from gpt-4 to gpt-5", ...)]
```

---

## Changelog Renderer

`ChangelogRenderer` convierte una lista de `ConfigChange` en Markdown o JSON.

### Markdown

```python
from licit.changelog.renderer import ChangelogRenderer

renderer = ChangelogRenderer()
output = renderer.render(changes, fmt="markdown")
```

Estructura del output:
1. Header `# Agent Config Changelog`
2. Summary: `N change(s) across M file(s): X major, Y minor, Z patch`
3. Secciones por archivo (ordenadas alfabéticamente)
4. Dentro de cada archivo: ordenado por severidad (MAJOR primero), luego timestamp descendente
5. Footer con timestamp UTC de generación

### JSON

```python
output = renderer.render(changes, fmt="json")
```

Produce:
```json
{
  "changes": [
    {
      "file_path": "config.yaml",
      "field_path": "model",
      "old_value": "gpt-4",
      "new_value": "gpt-5",
      "severity": "major",
      "description": "Changed: model from gpt-4 to gpt-5",
      "timestamp": "2026-03-10T00:00:00+00:00",
      "commit_sha": "abc1234"
    }
  ]
}
```

`ensure_ascii=False` para soporte completo de Unicode (ñ, ü, 日本語, etc.).

---

## Configuración

```yaml
changelog:
  enabled: true
  watch_files:
    - CLAUDE.md
    - .cursorrules
    - .cursor/rules
    - AGENTS.md
    - .github/copilot-instructions.md
    - .github/agents/*.md
    - .architect/config.yaml
    - architect.yaml
  output_path: .licit/changelog.md
```

| Campo | Tipo | Default | Descripción |
|---|---|---|---|
| `enabled` | bool | `true` | Habilitar monitoreo |
| `watch_files` | list[str] | (8 patrones) | Archivos/globs a monitorear |
| `output_path` | str | `.licit/changelog.md` | Ruta del changelog generado |

---

## Integración con compliance

El changelog de configuraciones de agentes alimenta directamente el `EvidenceBundle`:

| Campo del bundle | Qué aporta changelog |
|---|---|
| `has_changelog` | `True` si existe changelog generado |
| `changelog_entry_count` | Número de entradas en el changelog |

Estos campos son evaluados por los frameworks de compliance:

- **EU AI Act Art. 13** (Transparencia): Registro de cambios en configuración de agentes IA
- **EU AI Act Art. 26** (Obligaciones de deployers): Monitoreo de configuración
- **OWASP ASI-01** (Excessive Agency): Rastreo de cambios en guardrails y permisos
- **OWASP ASI-06** (Insufficient Monitoring): Trail de cambios como evidencia de monitoreo

---

## Testing

93 tests cubren el sistema de changelog:

| Módulo | Tests | Archivo |
|---|---|---|
| Watcher | 12 | `tests/test_changelog/test_watcher.py` |
| Differ | 19 | `tests/test_changelog/test_differ.py` |
| Classifier | 22 | `tests/test_changelog/test_classifier.py` |
| Renderer | 10 | `tests/test_changelog/test_renderer.py` |
| Integration | 3 | `tests/test_changelog/test_integration.py` |
| QA Edge Cases | 27 | `tests/test_changelog/test_qa_edge_cases.py` |
| **Total** | **93** | |

Los tests incluyen:
- Unit tests por módulo
- Edge cases (Unicode, archivos vacíos, timestamps timezone-aware, single-commit files, non-dict roots, fenced code blocks)
- Regression tests para 7 bugs encontrados en QA
- Tests de integración CLI (con y sin git repo)
- Tests de integración full pipeline (markdown + JSON + empty)
