# Sistema de Provenance

Sistema de trazabilidad de código para identificar y documentar qué código fue escrito por IA y qué por humanos.

> **Estado**: **Funcional** desde v0.2.0 (Fase 2 completada).

---

## Visión general

El sistema de provenance responde a la pregunta: **¿quién escribió este código?** Analiza el historial de git y logs de sesión de agentes IA para clasificar cada archivo como `ai`, `human` o `mixed`, con un score de confianza entre 0.0 y 1.0.

```bash
licit trace --stats
```

```
Analyzing git history...
Records: 45 files analyzed
AI-generated: 18 (40.0%)
Human-written: 22 (48.9%)
Mixed: 5 (11.1%)

AI tools detected: claude-code (15), cursor (3)
Models detected: claude-sonnet-4 (12), claude-opus-4 (3), gpt-4o (3)

Stored in .licit/provenance.jsonl
```

---

## Arquitectura

El sistema se compone de 8 módulos en `src/licit/provenance/`:

```
provenance/
├── heuristics.py          # Motor de 6 heurísticas de detección AI
├── git_analyzer.py        # Parser de git log con análisis heurístico
├── store.py               # Store JSONL deduplicado
├── attestation.py         # Firmado HMAC-SHA256 + Merkle tree
├── tracker.py             # Orquestador del pipeline completo
├── report.py              # Generador de reportes Markdown
└── session_readers/
    ├── base.py            # Protocol SessionReader
    └── claude_code.py     # Reader para Claude Code
```

### Flujo de datos

```
Git Log ──→ GitAnalyzer ──→ ProvenanceRecord[] ─┐
                                                 ├──→ ProvenanceTracker ──→ Store
Session Logs ──→ SessionReader ──→ Records[] ───┘          │
                                                           ├──→ Attestation (HMAC + Merkle)
                                                           └──→ Report (Markdown)
```

---

## Motor de heurísticas

`AICommitHeuristics` aplica 6 heurísticas independientes a cada commit de git. Cada heurística produce un score (0.0-1.0) y un peso relativo.

### Heurísticas

| # | Nombre | Peso | Qué detecta |
|---|---|---|---|
| H1 | Author pattern | 3.0 | Nombres de autor AI: `claude`, `copilot`, `cursor`, `bot`, `devin`, `aider`, `[bot]` |
| H2 | Message pattern | 1.5 | Patrones de commit: conventional commits, `[ai]`, `implement`, `generate`, `Co-authored-by` en subject |
| H3 | Bulk changes | 2.0 | Cambios masivos: >20 archivos **y** >500 líneas en un solo commit |
| H4 | Co-author | 3.0 | Trailer `Co-authored-by:` con keywords AI en el body del commit |
| H5 | File patterns | 1.0 | Todos los archivos modificados son test files (`test_`, `_test.`, `.spec.`) |
| H6 | Time pattern | 0.5 | Commits entre 1:00 AM y 5:00 AM |

### Cálculo del score

Solo las heurísticas que producen señal (score > 0) participan en el promedio ponderado:

```python
signaling = [h for h in results if h.score > 0]
total_weight = sum(h.weight for h in signaling)
final_score = sum(h.score * h.weight for h in signaling) / total_weight
```

Si ninguna heurística señaliza, el score final es 0.0 (humano).

### Clasificación

| Score | Clasificación |
|---|---|
| >= 0.7 | `ai` — Código probablemente generado por IA |
| >= 0.5 | `mixed` — Código con contribución mixta |
| < 0.5 | `human` — Código probablemente humano |

> El umbral configurable `confidence_threshold` (default: 0.6) afecta al filtrado en reportes, no a la clasificación base.

---

## Git Analyzer

`GitAnalyzer` parsea el historial de git y aplica las heurísticas a cada commit.

### Parsing de git log

Ejecuta `git log` con un formato personalizado usando separadores hexadecimales (`%x00`, `%x01`) para parsear campos de forma robusta:

```
git log --format="%x00%x01H%x01an%x01ae%x01aI%x01s%x01b" --numstat
```

Campos extraídos en `CommitInfo`:
- `sha`: Hash del commit
- `author` / `author_email`: Autor
- `date`: Fecha ISO 8601
- `message`: Subject del commit
- `files_changed`: Lista de archivos modificados
- `insertions` / `deletions`: Líneas añadidas/eliminadas
- `co_authors`: Co-autores extraídos del body (`Co-authored-by:`)

### Opciones

| Opción | CLI flag | Descripción |
|---|---|---|
| `since` | `--since` | Analizar commits desde fecha (YYYY-MM-DD) o tag |
| Timeout | — | 30 segundos para `git log` (previene bloqueos en repos masivos) |

### Resultado por archivo

Para cada archivo, se toma el **score máximo** entre todos los commits que lo modificaron. El método de detección es siempre `ProvenanceSource.GIT_INFER`.

---

## Session Readers

Los session readers extraen información de proveniencia directamente de los logs de sesión de agentes IA.

### Protocol

```python
class SessionReader(Protocol):
    def can_read(self, path: Path) -> bool: ...
    def read_sessions(self, path: Path) -> list[ProvenanceRecord]: ...
```

### Claude Code Reader

Lee archivos JSONL de sesión de Claude Code (típicamente en `~/.claude/projects/`).

**Campos extraídos:**
- Archivos modificados (de tool calls `Write`, `Edit`)
- Modelo utilizado (`claude-sonnet-4`, `claude-opus-4`, etc.)
- Herramienta: `claude-code`
- ID de sesión
- Coste estimado (si disponible)

**Configuración:**
```yaml
provenance:
  methods:
    - git-infer
    - session-log
  session_dirs:
    - ~/.claude/projects/
```

### Extensibilidad

Para añadir soporte para otro agente (ej. Cursor), implementar el Protocol `SessionReader` y registrarlo en `ProvenanceTracker`.

---

## Store JSONL

`ProvenanceStore` almacena registros de proveniencia en formato JSONL (JSON Lines) con deduplicación automática por archivo.

### Formato

Cada línea es un objeto JSON independiente (un registro por archivo único):

```json
{"file_path": "src/app.py", "source": "ai", "confidence": 0.85, "method": "git-infer", "timestamp": "2026-03-10T14:30:00", "model": "claude-sonnet-4", "agent_tool": "claude-code"}
{"file_path": "tests/test_app.py", "source": "human", "confidence": 0.0, "method": "git-infer", "timestamp": "2026-03-10T14:30:00"}
```

### Operaciones

| Operación | Método | Descripción |
|---|---|---|
| Save | `save(records)` | Fusiona registros con los existentes (dedup por file path, latest wins) y reescribe |
| Load | `load_all()` | Lee todos los registros del store |
| Stats | `get_stats()` | Estadísticas de proveniencia (ai/human/mixed) |
| By file | `get_by_file(path)` | Registros de un archivo específico |

### Características

- **Merge + dedup**: Cada `save()` fusiona con registros existentes — el más reciente por archivo gana. El store no crece con ejecuciones repetidas.
- **Inmutable por registro**: Cada registro tiene timestamp y firma (si habilitado)
- **Serialización segura**: Usa `default=str` para datetime y otros tipos
- **Manejo de errores**: `PermissionError` y otros errores de I/O se reportan con mensaje limpio
- **Ruta configurable**: `provenance.store_path` en `.licit.yaml`

---

## Attestation (Firmado criptográfico)

`ProvenanceAttestor` proporciona firmado HMAC-SHA256 individual y verificación batch con Merkle tree.

### Firmado individual

```python
from licit.provenance.attestation import ProvenanceAttestor

attestor = ProvenanceAttestor()  # Auto-genera key si no existe

# Firmar un registro
data = {"file": "app.py", "source": "ai", "confidence": 0.85}
signature = attestor.sign_record(data)

# Verificar
assert attestor.verify_record(data, signature)
```

### Merkle tree (batch)

Para verificar integridad de un conjunto de registros:

```python
records = [record1, record2, record3, record4]
root_hash = attestor.sign_batch(records)
```

```
         root_hash
        /         \
    hash_01      hash_23
    /    \       /    \
 hash_0 hash_1 hash_2 hash_3
   |      |      |      |
 rec_0  rec_1  rec_2  rec_3
```

- Cada registro se serializa como JSON canónico (`sort_keys=True, default=str`)
- SHA256 de cada registro → hojas del árbol
- Pares se concatenan y re-hashean hasta la raíz
- Registros impares: el último se duplica
- Verificación timing-safe con `hmac.compare_digest`

### Gestión de claves

La clave de firmado se resuelve en este orden:

1. **Path explícito** en config: `provenance.sign_key_path`
2. **Fallback local**: `.licit/.signing-key` en el proyecto
3. **Auto-generación**: 32 bytes aleatorios con `os.urandom(32)`

```yaml
# Ejemplo con clave explícita
provenance:
  sign: true
  sign_key_path: ~/.licit/signing-key
```

---

## Tracker (Orquestador)

`ProvenanceTracker` orquesta el pipeline completo:

```python
from licit.provenance.tracker import ProvenanceTracker

tracker = ProvenanceTracker(config=config, project_root="/path/to/project")
stats = tracker.run(since="2026-01-01")
```

### Pipeline

1. **Git analysis**: Ejecuta `GitAnalyzer` para analizar commits
2. **Session reading**: Lee logs de sesión si `session-log` está en `methods`
3. **Merge**: Combina resultados de git y sesiones (prioridad a sesiones si hay conflicto)
4. **Signing**: Firma cada registro si `sign: true`
5. **Storage**: Almacena en JSONL via `ProvenanceStore`
6. **Stats**: Retorna estadísticas agregadas

### Estadísticas retornadas

```python
{
    "total_files": 45,
    "ai_count": 18,
    "human_count": 22,
    "mixed_count": 5,
    "ai_percentage": 40.0,
    "human_percentage": 48.9,
    "mixed_percentage": 11.1,
    "tools_detected": {"claude-code": 15, "cursor": 3},
    "models_detected": {"claude-sonnet-4": 12, "claude-opus-4": 3, "gpt-4o": 3},
}
```

---

## Report

`ProvenanceReportGenerator` genera reportes Markdown a partir de los registros almacenados.

### Contenido del reporte

1. **Resumen**: Totales y porcentajes por clasificación
2. **Tabla detallada**: Archivo, fuente, confianza, método, modelo, herramienta
3. **Herramientas detectadas**: Frecuencia de cada agente IA
4. **Modelos detectados**: Frecuencia de cada modelo

### Generación

```bash
licit trace --report
# Genera .licit/reports/provenance.md
```

```python
from licit.provenance.report import ProvenanceReportGenerator

generator = ProvenanceReportGenerator()
markdown = generator.generate(records, project_name="mi-proyecto")
```

---

## Configuración completa

```yaml
provenance:
  enabled: true
  methods:
    - git-infer              # Heurísticas de git history
    - session-log            # Logs de sesión de agentes
  session_dirs:
    - ~/.claude/projects/    # Directorio con logs de Claude Code
  sign: true                 # Firmar registros con HMAC-SHA256
  sign_key_path: ~/.licit/signing-key
  confidence_threshold: 0.6  # Umbral de confianza
  store_path: .licit/provenance.jsonl
```

---

## Integración con compliance

La evidencia de provenance alimenta directamente el `EvidenceBundle`:

| Campo del bundle | Qué aporta provenance |
|---|---|
| `has_provenance` | `True` si existe store con registros |
| `provenance_stats` | Estadísticas agregadas (totales, porcentajes, herramientas, modelos) |

Estos campos son evaluados por los frameworks de compliance:

- **EU AI Act Art. 10** (Datos y gobernanza): Trazabilidad de origen del código
- **EU AI Act Art. 13** (Transparencia): Disclosure de uso de IA en desarrollo
- **OWASP ASI-06** (Insufficient Monitoring): Trail de proveniencia como evidencia de monitoreo
- **OWASP ASI-10** (Insufficient Logging): Registros estructurados de actividad de agentes

---

## Testing

167 tests cubren el sistema de provenance:

| Módulo | Tests | Archivo |
|---|---|---|
| Heurísticas | 23 | `tests/test_provenance/test_heuristics.py` |
| Git Analyzer | 15 | `tests/test_provenance/test_git_analyzer.py` |
| Store | 15 | `tests/test_provenance/test_store.py` |
| Attestation | 13 | `tests/test_provenance/test_attestation.py` |
| Tracker | 7 | `tests/test_provenance/test_tracker.py` |
| Session Reader | 13 | `tests/test_provenance/test_session_reader.py` |
| QA Edge Cases | 81 | `tests/test_provenance/test_qa_edge_cases.py` |
| **Total** | **167** | |

Los tests incluyen:
- Unit tests por módulo
- Edge cases (Unicode, archivos vacíos, claves inválidas, repos sin commits, etc.)
- Regression tests para 9 bugs encontrados en QA
- Tests de integración cross-módulo
