# Modelos de datos

licit separa sus modelos en dos categorías por diseño:
- **Pydantic v2**: Solo para configuración (validación estricta, serialización YAML/JSON).
- **Dataclasses**: Para modelos de dominio (ligeros, sin dependencias externas).

---

## Enums

Todos los enums usan `StrEnum` (Python 3.12+) para serialización directa a string.

### ComplianceStatus

Estado de cumplimiento de un requisito regulatorio.

```python
class ComplianceStatus(StrEnum):
    COMPLIANT     = "compliant"       # Requisito totalmente cumplido
    PARTIAL       = "partial"         # Requisito parcialmente cumplido
    NON_COMPLIANT = "non-compliant"   # Requisito no cumplido
    NOT_APPLICABLE = "n/a"            # Requisito no aplica al proyecto
    NOT_EVALUATED = "not-evaluated"   # Requisito aún no evaluado
```

**Uso**: En `ControlResult.status` y `GapItem.status`.

### ChangeSeverity

Severidad de un cambio en configuración de agente IA.

```python
class ChangeSeverity(StrEnum):
    MAJOR = "major"   # Cambio de modelo, eliminación de guardrail
    MINOR = "minor"   # Cambio de prompt, nueva regla añadida
    PATCH = "patch"   # Ajuste de parámetro, formateo
```

**Uso**: En `ConfigChange.severity`.

### ProvenanceSource

Método por el cual se determinó la proveniencia del código.

```python
class ProvenanceSource(StrEnum):
    GIT_INFER   = "git-infer"     # Inferido por heurísticas de git
    SESSION_LOG = "session-log"   # Leído de logs de sesión del agente
    GIT_AI      = "git-ai"        # Anotaciones de git-ai
    MANUAL      = "manual"        # Anotado manualmente
    CONNECTOR   = "connector"     # Información de architect/vigil
```

**Uso**: En `ProvenanceRecord.method`.

---

## Dataclasses de dominio

### ProvenanceRecord

Registro de proveniencia de un archivo o fragmento de código.

```python
@dataclass
class ProvenanceRecord:
    file_path: str                              # Ruta al archivo
    source: str                                 # "ai", "human", "mixed"
    confidence: float                           # Confianza (0.0-1.0)
    method: ProvenanceSource                    # Cómo se determinó
    timestamp: datetime                         # Cuándo se registró
    lines_range: tuple[int, int] | None = None  # Rango de líneas (opcional)
    model: str | None = None                    # Modelo IA: "claude-sonnet-4"
    agent_tool: str | None = None               # Herramienta: "claude-code"
    session_id: str | None = None               # ID de sesión
    spec_ref: str | None = None                 # Referencia a spec de intake
    cost_usd: float | None = None               # Coste de generación
    signature: str | None = None                # Firma HMAC-SHA256
```

**Ejemplo:**
```python
record = ProvenanceRecord(
    file_path="src/app/main.py",
    source="ai",
    confidence=0.92,
    method=ProvenanceSource.GIT_INFER,
    timestamp=datetime.now(),
    model="claude-sonnet-4",
    agent_tool="claude-code",
)
```

### ConfigChange

Cambio detectado en un archivo de configuración de agente IA.

```python
@dataclass
class ConfigChange:
    file_path: str               # Ruta al archivo de config
    field_path: str              # Campo cambiado: "model", "guardrails.protected_files"
    old_value: str | None        # Valor anterior
    new_value: str | None        # Valor nuevo
    severity: ChangeSeverity     # MAJOR / MINOR / PATCH
    description: str             # Descripción legible del cambio
    timestamp: datetime          # Cuándo ocurrió
    commit_sha: str | None = None  # SHA del commit
```

**Ejemplo:**
```python
change = ConfigChange(
    file_path="CLAUDE.md",
    field_path="model",
    old_value="claude-sonnet-4",
    new_value="claude-opus-4",
    severity=ChangeSeverity.MAJOR,
    description="Modelo de IA actualizado de Sonnet a Opus",
    timestamp=datetime.now(),
    commit_sha="abc1234",
)
```

### ControlRequirement

Requisito regulatorio individual de un marco de compliance.

```python
@dataclass
class ControlRequirement:
    id: str                          # "ART-9-1", "ASI-01"
    framework: str                   # "eu-ai-act", "owasp-agentic"
    name: str                        # Nombre del requisito
    description: str                 # Descripción completa
    article_ref: str | None = None   # "Article 9(1)" para EU AI Act
    category: str | None = None      # "risk-management", "transparency"
```

### ControlResult

Resultado de evaluar un requisito contra el proyecto.

```python
@dataclass
class ControlResult:
    requirement: ControlRequirement    # El requisito evaluado
    status: ComplianceStatus           # Estado de cumplimiento
    evidence: str                      # Qué prueba el cumplimiento
    details: str = ""                  # Detalles adicionales
    source: str = "auto"               # "auto", "architect", "vigil", "manual"
    recommendations: list[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=datetime.now)
```

### ComplianceSummary

Resumen agregado de compliance para un marco regulatorio.

```python
@dataclass
class ComplianceSummary:
    framework: str              # "eu-ai-act", "owasp-agentic"
    total_controls: int         # Total de controles
    compliant: int              # Cumplidos
    partial: int                # Parcialmente cumplidos
    non_compliant: int          # No cumplidos
    not_applicable: int         # No aplican
    not_evaluated: int          # No evaluados
    compliance_rate: float      # Porcentaje de cumplimiento
    evaluated_at: datetime = field(default_factory=datetime.now)
```

**Cálculo de compliance_rate:**
```
compliance_rate = compliant / (total - not_applicable - not_evaluated) * 100
```

### GapItem

Brecha de compliance identificada con recomendación.

```python
@dataclass
class GapItem:
    requirement: ControlRequirement    # Requisito con brecha
    status: ComplianceStatus           # Estado actual
    gap_description: str               # Qué falta
    recommendation: str                # Cómo solucionarlo
    effort: str                        # "low", "medium", "high"
    tools_suggested: list[str] = field(default_factory=list)
    priority: int = 0                  # Prioridad (1 = máxima)
```

---

## Modelos de provenance (Fase 2)

### CommitInfo

Commit de git parseado con metadatos para análisis heurístico.

```python
@dataclass
class CommitInfo:
    sha: str                     # Hash SHA completo del commit
    author: str                  # Nombre del autor
    author_email: str            # Email del autor
    date: datetime               # Fecha del commit
    message: str                 # Asunto del commit
    files_changed: list[str]     # Archivos modificados
    insertions: int              # Líneas añadidas
    deletions: int               # Líneas eliminadas
    co_authors: list[str] = []   # Co-autores (extraídos del body)
```

**Uso**: Producido por `GitAnalyzer._parse_git_log()`, consumido por `AICommitHeuristics.score_commit()`.

### HeuristicResult

Resultado de aplicar una heurística individual a un commit.

```python
@dataclass
class HeuristicResult:
    name: str       # Identificador: "author_pattern", "message_pattern", etc.
    score: float    # Contribución al score final (0.0-1.0)
    weight: float   # Peso relativo de esta heurística
    reason: str     # Explicación legible del resultado
```

**Uso**: Producido internamente por cada heurística, agregado en `score_commit()`.

**Cálculo del score final**: Solo se promedian las heurísticas con score > 0 (señalizantes):
```python
signaling = [r for r in results if r.score > 0]
total_weight = sum(r.weight for r in signaling)
score = sum(r.score * r.weight for r in signaling) / total_weight
```

---

## Modelos de changelog (Fase 3)

### ConfigSnapshot

Snapshot de un archivo de configuración en un punto del historial git.

```python
@dataclass
class ConfigSnapshot:
    path: str          # Ruta relativa del archivo
    content: str       # Contenido del archivo en ese commit
    commit_sha: str    # Hash SHA del commit
    timestamp: datetime # Fecha del commit (timezone-aware desde git)
    author: str        # Autor del commit
```

**Uso**: Producido por `ConfigWatcher._get_file_history()`, consumido por `ChangeClassifier.classify_changes()`.

### FieldDiff

Diferencia a nivel de campo entre dos versiones de un archivo de configuración.

```python
@dataclass
class FieldDiff:
    field_path: str           # "model", "llm.provider", "section:Rules", "(content)"
    old_value: str | None     # Valor anterior (None si es adición)
    new_value: str | None     # Valor nuevo (None si es eliminación)
    is_addition: bool = False # Campo nuevo
    is_removal: bool = False  # Campo eliminado
```

**Uso**: Producido por `diff_configs()`, consumido por `ChangeClassifier._classify_field()`.

**Convenciones de `field_path`:**
- YAML/JSON: dotted path (`model`, `llm.model`, `guardrails.protected_files`)
- Markdown: `section:{heading}` (ej: `section:Rules`, `section:Instructions`)
- Texto plano / Markdown sin headings: `(content)`
- Errores de parseo: `(parse-error)`
- Roots no-dict: `(root)`

---

## Modelos de detección

Usados por `ProjectDetector` para describir el contexto del proyecto.

### ProjectContext

Contexto completo del proyecto auto-detectado.

```python
@dataclass
class ProjectContext:
    root_dir: str
    name: str
    languages: list[str]           # ["python", "javascript", "go", ...]
    frameworks: list[str]          # ["fastapi", "react", "express", ...]
    package_managers: list[str]    # ["pip", "npm", "cargo", ...]
    agent_configs: list[AgentConfigFile]
    has_architect: bool
    architect_config_path: str | None
    cicd: CICDConfig
    test_framework: str | None     # "pytest", "jest", "vitest"
    test_dirs: list[str]
    security: SecurityTooling
    git_initialized: bool
    total_commits: int
    total_contributors: int
    first_commit_date: str | None
    last_commit_date: str | None
```

### AgentConfigFile

Archivo de configuración de agente IA detectado.

```python
@dataclass
class AgentConfigFile:
    path: str            # Ruta al archivo
    agent_type: str      # "claude-code", "cursor", "architect", "copilot", "generic"
    exists: bool = True
```

### CICDConfig

Configuración de CI/CD detectada.

```python
@dataclass
class CICDConfig:
    platform: str                    # "github-actions", "gitlab-ci", "jenkins", etc.
    config_path: str | None = None
    has_ai_steps: bool = False       # CI/CD ejecuta agentes IA
```

### SecurityTooling

Herramientas de seguridad detectadas en el proyecto.

```python
@dataclass
class SecurityTooling:
    has_vigil: bool = False
    has_semgrep: bool = False
    has_snyk: bool = False
    has_codeql: bool = False
    has_trivy: bool = False
    has_eslint_security: bool = False
    vigil_config_path: str | None = None
    sarif_files: list[str] = field(default_factory=list)
```

---

## EvidenceBundle

Recopilación completa de evidencia del proyecto (18 campos). Usado por los evaluadores para determinar compliance.

```python
@dataclass
class EvidenceBundle:
    # Provenance
    has_provenance: bool = False
    provenance_stats: dict[str, object] = field(default_factory=dict)

    # Changelog
    has_changelog: bool = False
    changelog_entry_count: int = 0

    # Documentación regulatoria
    has_fria: bool = False
    fria_path: str | None = None
    has_annex_iv: bool = False
    annex_iv_path: str | None = None

    # Guardrails
    has_guardrails: bool = False
    guardrail_count: int = 0

    # Quality assurance
    has_quality_gates: bool = False
    quality_gate_count: int = 0
    has_budget_limits: bool = False
    has_dry_run: bool = False
    has_rollback: bool = False

    # Auditoría
    has_audit_trail: bool = False
    audit_entry_count: int = 0
    has_otel: bool = False

    # Revisión humana
    has_human_review_gate: bool = False

    # Trazabilidad de requisitos
    has_requirements_traceability: bool = False

    # Seguridad (SARIF)
    security_findings_total: int = 0
    security_findings_critical: int = 0
    security_findings_high: int = 0
```

---

## Modelos Pydantic (Configuración)

Los modelos de configuración están documentados en detalle en la [Guía de configuración](configuracion.md). Aquí se lista la jerarquía:

```
LicitConfig (raíz)
├── provenance: ProvenanceConfig
├── changelog: ChangelogConfig
├── frameworks: FrameworkConfig
├── connectors: ConnectorsConfig
│   ├── architect: ConnectorArchitectConfig
│   └── vigil: ConnectorVigilConfig
├── fria: FRIAConfig
├── annex_iv: AnnexIVConfig
└── reports: ReportConfig
```

Todos los modelos Pydantic usan `model_config = ConfigDict(extra="ignore")` implícitamente y permiten campos extra en el YAML sin error (se ignoran silenciosamente).

---

## Modelos de connectors (Fase 7)

### ConnectorResult

Resultado de una operación de lectura de un connector.

```python
@dataclass
class ConnectorResult:
    connector_name: str              # "architect", "vigil"
    files_read: int = 0              # Archivos leídos exitosamente
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True si leyó archivos y no hubo errores."""
        return self.files_read > 0 and len(self.errors) == 0

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
```

**Uso**: Retornado por `Connector.collect()`, expuesto via `EvidenceCollector.connector_results`.

### ArchitectReport

Resumen parseado de un report JSON de architect.

```python
@dataclass
class ArchitectReport:
    path: str
    task_id: str | None = None
    status: str | None = None
    model: str | None = None
    cost_usd: float | None = None
    files_changed: list[str] = field(default_factory=list)
    timestamp: str | None = None
```

### AuditEntry

Entrada individual del audit log JSONL de architect.

```python
@dataclass
class AuditEntry:
    event: str                                   # "task_start", "file_write", etc.
    timestamp: str | None = None
    details: dict[str, object] = field(default_factory=dict)
```

### SARIFFinding

Hallazgo individual de un archivo SARIF.

```python
@dataclass
class SARIFFinding:
    rule_id: str                     # "VIGIL-001", "semgrep-rule-xyz"
    level: str                       # "error", "warning", "note", "none"
    message: str
    file_path: str | None = None     # URI del archivo afectado
    start_line: int | None = None    # Línea de inicio
    tool_name: str = ""              # Nombre del tool del run SARIF
```

### SARIFSummary

Resumen de findings de un run SARIF.

```python
@dataclass
class SARIFSummary:
    tool_name: str
    total: int = 0
    critical: int = 0               # level == "error"
    high: int = 0                   # level == "warning"
    medium: int = 0                 # level == "note"
    low: int = 0                    # level == otro
    findings: list[SARIFFinding] = field(default_factory=list)
```

### Connector Protocol

Protocol que todos los connectors implementan.

```python
@runtime_checkable
class Connector(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def enabled(self) -> bool: ...

    def available(self) -> bool: ...

    def collect(self, evidence: EvidenceBundle) -> ConnectorResult: ...
```

**Implementaciones**: `ArchitectConnector`, `VigilConnector`.
