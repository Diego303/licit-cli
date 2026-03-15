# Conectores

## Visión general

Los conectores de licit son integraciones read-only con herramientas externas que enriquecen la evidencia de compliance. Son **opcionales** — licit funciona completamente sin ellos — pero cuando están habilitados, aportan datos que mejoran la evaluación.

> **Principio**: Los conectores **enriquecen, no habilitan**. Ninguna funcionalidad core depende de un conector.

### Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    EvidenceCollector                      │
│                                                          │
│  ┌─────────────────┐   Con LicitConfig    Sin config    │
│  │  _run_connectors │──┬── enabled ──→ Connector formal │
│  └─────────────────┘  │                                  │
│                        └── disabled ──→ Inline temporal  │
│                            o absent    (delega a clase   │
│                                         connector)       │
└──────────────┬───────────────────────────┬──────────────┘
               │                           │
    ┌──────────▼──────────┐    ┌───────────▼──────────┐
    │ ArchitectConnector   │    │  VigilConnector       │
    │                      │    │                       │
    │ _read_reports()      │    │ _resolve_sarif_paths()│
    │ _read_audit_log()    │    │ _read_sarif()         │
    │ _read_config()       │    │ _read_sbom()          │
    └──────────────────────┘    └───────────────────────┘
```

### Protocol Connector

Todos los conectores implementan el Protocol `Connector`:

```python
@runtime_checkable
class Connector(Protocol):
    @property
    def name(self) -> str: ...        # "architect", "vigil"

    @property
    def enabled(self) -> bool: ...    # Desde config

    def available(self) -> bool: ...  # ¿Datos en disco?

    def collect(self, evidence: EvidenceBundle) -> ConnectorResult: ...
```

### ConnectorResult

Cada ejecución de `collect()` retorna un `ConnectorResult`:

```python
@dataclass
class ConnectorResult:
    connector_name: str
    files_read: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True si leyó ≥1 archivo sin errores."""
        return self.files_read > 0 and len(self.errors) == 0
```

---

## Architect Connector

### Qué es architect

[architect](https://github.com/Diego303/architect) es un agente de codificación autónomo que produce reports de ejecución, audit logs, y un config YAML con guardrails y controles de calidad.

### Fuentes de datos

| Fuente | Formato | Qué extrae | Evidencia |
|---|---|---|---|
| **Reports** | `reports_dir/*.json` | Tareas completadas (task_id, model, cost, files) | `has_audit_trail`, `audit_entry_count` |
| **Audit log** | `audit_log` (JSONL) | Eventos del ciclo de vida de tareas | `has_audit_trail`, `audit_entry_count` |
| **Config** | `config_path` (YAML) | Guardrails, quality gates, budget, capabilities | `guardrail_count`, `has_quality_gates`, `has_budget_limits`, `has_dry_run`, `has_rollback` |

### Campos del config que se extraen

```yaml
# .architect/config.yaml
model: claude-sonnet-4
provider: anthropic

guardrails:
  protected_files:              # → guardrail_count += N
    - .env
    - secrets.yaml
  blocked_commands:             # → guardrail_count += N
    - rm -rf
    - DROP TABLE
  code_rules:                   # → guardrail_count += N
    - no-eval
    - no-exec
  quality_gates:                # → has_quality_gates, quality_gate_count
    - lint
    - typecheck
    - test

costs:
  budget_usd: 50.0              # → has_budget_limits

dry_run: true                   # → has_dry_run (default True si ausente)
rollback: true                  # → has_rollback (default True si ausente)
```

> **Nota**: `guardrail_count` es aditivo (`+=`). Si otros conectores también contribuyen guardrails, se suman.

### Formato de reports JSON

Cada archivo en `reports_dir/` debe ser un JSON object con campos opcionales:

```json
{
  "task_id": "task-001",
  "status": "completed",
  "model": "claude-sonnet-4",
  "cost_usd": 0.42,
  "files_changed": ["src/auth.py", "tests/test_auth.py"],
  "timestamp": "2026-03-10T14:30:00Z"
}
```

Todos los campos son opcionales. Un `{}` vacío es válido y se cuenta como un audit entry.

### Formato de audit log JSONL

Cada línea es un JSON object independiente:

```jsonl
{"event": "task_start", "timestamp": "2026-03-10T14:00:00Z", "task_id": "task-001"}
{"event": "file_write", "timestamp": "2026-03-10T14:15:00Z", "path": "src/auth.py"}
{"event": "task_complete", "timestamp": "2026-03-10T14:30:00Z", "cost_usd": 0.42}
```

Líneas malformadas se registran como error pero no abortan la lectura.

### Configuración

```yaml
connectors:
  architect:
    enabled: true
    reports_dir: .architect/reports         # Default
    config_path: .architect/config.yaml     # Default si no configurado
    audit_log: .architect/audit.jsonl       # Opcional
```

### Habilitación

```bash
licit connect architect
# → architect data found at: .architect/reports
# → Connector 'architect' enabled.
```

`licit init` auto-detecta `.architect/` y habilita el conector automáticamente.

---

## Vigil Connector

### Qué es vigil

[vigil](https://github.com/vigil-ai/vigil) es un security scanner para código generado por IA que produce hallazgos en formato SARIF (Static Analysis Results Interchange Format).

### SARIF 2.1.0

El conector parsea cualquier archivo SARIF 2.1.0, no solo los de vigil. Funciona con Semgrep, CodeQL, Snyk, y cualquier herramienta que produzca SARIF estándar.

### Resolución de paths

```
1. sarif_path explícito (archivo) → lo lee
2. sarif_path explícito (directorio) → lee todos los *.sarif
3. Auto-detected (ProjectContext.security.sarif_files) → lee los no duplicados
```

### Mapeo de severidad

| Level SARIF | Campo EvidenceBundle | Clasificación |
|---|---|---|
| `error` | `security_findings_critical` | Crítico |
| `warning` | `security_findings_high` | Alto |
| `note` | (solo en total) | Medio |
| otro | (solo en total) | Bajo |

### SBOM (Software Bill of Materials)

El conector lee SBOM en formato CycloneDX JSON. En V0 solo valida la estructura. En V1 alimentará la evaluación de OWASP ASI03 (Supply Chain Vulnerabilities).

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.4",
  "components": [
    {"type": "library", "name": "click", "version": "8.1.7"},
    {"type": "library", "name": "pydantic", "version": "2.6.0"}
  ]
}
```

### Configuración

```yaml
connectors:
  vigil:
    enabled: true
    sarif_path: reports/security/    # Archivo o directorio
    sbom_path: sbom.json             # CycloneDX JSON
```

### Habilitación

```bash
licit connect vigil
# → vigil data found
# → Connector 'vigil' enabled.
```

`licit init` auto-detecta `.vigil.yaml` y habilita el conector automáticamente.

---

## Cómo los conectores alimentan compliance

### EU AI Act

| Artículo | Evidencia de architect | Evidencia de vigil |
|---|---|---|
| Art. 9 (Riesgos) | Guardrails, quality gates, budget | Security scanning presente |
| Art. 12 (Logging) | Audit trail (reports + audit log) | — |
| Art. 13 (Transparencia) | — | — |
| Art. 14 (Oversight) | Dry-run, rollback, quality gates | — |

### OWASP Agentic Top 10

| Riesgo | Evidencia de architect | Evidencia de vigil |
|---|---|---|
| ASI01 (Excessive Agency) | Guardrails, budget, quality gates | — |
| ASI02 (Prompt Injection) | Guardrails | Security findings |
| ASI03 (Supply Chain) | — | SBOM (V1) |
| ASI04 (Logging) | Audit trail | — |
| ASI07 (Sandboxing) | Guardrails (blocked commands) | — |
| ASI10 (Data Exposure) | Protected files | Security scanning |

---

## Desarrollar un conector custom (V1)

En V1, el plugin system permitirá registrar conectores custom. La interfaz será:

```python
from licit.connectors.base import Connector, ConnectorResult
from licit.core.evidence import EvidenceBundle

class MiConnector:
    name = "mi-tool"

    def __init__(self, root_dir: str, config: MiConfig) -> None:
        self.root = Path(root_dir)
        self.config = config

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def available(self) -> bool:
        return (self.root / ".mi-tool.yaml").exists()

    def collect(self, evidence: EvidenceBundle) -> ConnectorResult:
        result = ConnectorResult(connector_name=self.name)
        # ... leer datos y enriquecer evidence ...
        return result
```

El conector debe:
1. Implementar el Protocol `Connector` completo
2. Mutar `evidence` in-place (no retornar un nuevo bundle)
3. Reportar archivos leídos y errores en `ConnectorResult`
4. Manejar gracefully archivos faltantes o malformados
5. Usar `encoding="utf-8"` en todas las lecturas
6. Logear con `structlog.get_logger()`
