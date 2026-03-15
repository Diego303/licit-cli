# Uso programático (API Python)

licit está diseñado como CLI, pero todos sus módulos son importables y usables directamente desde Python. Esto es útil para:

- Integrar licit en pipelines custom
- Construir dashboards o wrappers
- Scripts de automatización de compliance
- Testing y validación programática

---

## Carga de configuración

```python
from licit.config.loader import load_config, save_config
from licit.config.schema import LicitConfig

# Cargar desde .licit.yaml (o defaults si no existe)
config = load_config()

# Cargar desde path explícito
config = load_config("/ruta/a/mi-config.yaml")

# Crear config por defecto y modificar
config = LicitConfig()
config.frameworks.owasp_agentic = False
config.connectors.architect.enabled = True
config.connectors.architect.config_path = ".architect/config.yaml"

# Guardar
save_config(config)
save_config(config, "/ruta/custom.yaml")
```

---

## Detección de proyecto

```python
from licit.core.project import ProjectDetector

detector = ProjectDetector()
context = detector.detect("/ruta/al/proyecto")

# Acceder a datos detectados
print(context.name)                  # "mi-app"
print(context.languages)             # ["python", "typescript"]
print(context.agent_configs)         # [AgentConfigFile(path="CLAUDE.md", ...)]
print(context.cicd.platform)         # "github-actions"
print(context.security.has_vigil)    # True
print(context.total_commits)         # 142
```

---

## Recolección de evidencia

```python
from licit.core.evidence import EvidenceCollector

# Sin config (inline detection)
collector = EvidenceCollector("/ruta/al/proyecto", context)
evidence = collector.collect()

# Con config (usa connectors formales)
collector = EvidenceCollector("/ruta/al/proyecto", context, config)
evidence = collector.collect()

# Verificar evidencia
print(evidence.has_provenance)              # True
print(evidence.has_guardrails)              # True
print(evidence.guardrail_count)             # 7
print(evidence.security_findings_total)     # 3
print(evidence.security_findings_critical)  # 1

# Resultados de connectors
for result in collector.connector_results:
    print(f"{result.connector_name}: {result.files_read} files, {len(result.errors)} errors")
```

---

## Provenance tracking

```python
from licit.provenance.tracker import ProvenanceTracker
from licit.provenance.store import ProvenanceStore

# Analizar
tracker = ProvenanceTracker("/ruta/al/proyecto", config.provenance)
records = tracker.analyze(since="2026-01-01")

# Estadísticas
for r in records:
    print(f"{r.file_path}: {r.source} (confidence={r.confidence:.2f}, tool={r.agent_tool})")

# Store directo
store = ProvenanceStore(".licit/provenance.jsonl")
stats = store.get_stats()
print(f"AI: {stats['ai_percentage']:.1f}%")

# Buscar por archivo
file_records = store.get_by_file("src/main.py")
```

---

## Evaluación de compliance

```python
from licit.frameworks.eu_ai_act.evaluator import EUAIActEvaluator
from licit.frameworks.owasp_agentic.evaluator import OWASPAgenticEvaluator
from licit.core.models import ComplianceStatus

# EU AI Act
eu_evaluator = EUAIActEvaluator()
results = eu_evaluator.evaluate(context, evidence)

for result in results:
    print(f"{result.requirement.id}: {result.status.value}")
    if result.status == ComplianceStatus.NON_COMPLIANT:
        for rec in result.recommendations:
            print(f"  → {rec}")

# OWASP
owasp_evaluator = OWASPAgenticEvaluator()
owasp_results = owasp_evaluator.evaluate(context, evidence)
```

---

## Reportes

```python
from licit.reports.unified import UnifiedReportGenerator
from licit.reports import markdown, json_fmt, html

# Generar reporte
generator = UnifiedReportGenerator(context, evidence, config)
report = generator.generate([eu_evaluator, owasp_evaluator])

# Renderizar
md_content = markdown.render(report)
json_content = json_fmt.render(report)
html_content = html.render(report)

# Acceder a datos del reporte
print(f"Overall: {report.overall_compliance_rate:.1f}%")
for fw in report.frameworks:
    print(f"  {fw.name}: {fw.summary.compliance_rate:.1f}%")
```

---

## Gap analysis

```python
from licit.reports.gap_analyzer import GapAnalyzer

analyzer = GapAnalyzer(context, evidence, config)
gaps = analyzer.analyze([eu_evaluator, owasp_evaluator])

for gap in gaps:
    print(f"[P{gap.priority}] {gap.requirement.id}: {gap.gap_description}")
    print(f"  → {gap.recommendation} (effort: {gap.effort})")
    print(f"  Tools: {', '.join(gap.tools_suggested)}")
```

---

## Connectors directos

```python
from licit.config.schema import ConnectorArchitectConfig, ConnectorVigilConfig
from licit.connectors.architect import ArchitectConnector
from licit.connectors.vigil import VigilConnector
from licit.core.evidence import EvidenceBundle

# Architect
arch_config = ConnectorArchitectConfig(
    enabled=True,
    config_path=".architect/config.yaml",
    audit_log=".architect/audit.jsonl",
)
arch = ArchitectConnector("/ruta/al/proyecto", arch_config)

if arch.available():
    ev = EvidenceBundle()
    result = arch.collect(ev)
    print(f"Guardrails: {ev.guardrail_count}, Audit entries: {ev.audit_entry_count}")

# Vigil
vig_config = ConnectorVigilConfig(enabled=True, sarif_path="results.sarif")
vig = VigilConnector("/ruta/al/proyecto", vig_config, sarif_files=["scan.sarif"])
result = vig.collect(ev)
print(f"Findings: {ev.security_findings_total} ({ev.security_findings_critical} critical)")
```

---

## Changelog de configs

```python
from licit.changelog.watcher import ConfigWatcher
from licit.changelog.classifier import ChangeClassifier
from licit.changelog.renderer import ChangelogRenderer

watcher = ConfigWatcher("/ruta/al/proyecto", ["CLAUDE.md", ".cursorrules"])
history = watcher.get_config_history(since="2026-01-01")

classifier = ChangeClassifier()
all_changes = []
for file_path, snapshots in history.items():
    for i in range(len(snapshots) - 1):
        changes = classifier.classify_changes(
            old_content=snapshots[i + 1].content,
            new_content=snapshots[i].content,
            file_path=file_path,
            commit_sha=snapshots[i].commit_sha,
            timestamp=snapshots[i].timestamp,
        )
        all_changes.extend(changes)

renderer = ChangelogRenderer()
print(renderer.render(all_changes, fmt="markdown"))
```

---

## FRIA y Annex IV

```python
from licit.frameworks.eu_ai_act.fria import FRIAGenerator
from licit.frameworks.eu_ai_act.annex_iv import AnnexIVGenerator

# FRIA (sin interactividad — pasar respuestas directamente)
fria_gen = FRIAGenerator(context, evidence)
# fria_gen.run_interactive()  # Solo funciona en terminal

# Annex IV
annex_gen = AnnexIVGenerator(context, evidence)
annex_gen.generate(
    output_path=".licit/annex-iv.md",
    organization="ACME Corp",
    product_name="WebApp",
)
```

---

## Notas importantes

1. **Todas las clases usan type hints estrictos** — aprovecha autocompletado del IDE.
2. **Los evaluadores son stateless** — puedes instanciar y usar en cualquier orden.
3. **EvidenceBundle es mutable** — los connectors lo mutan in-place.
4. **structlog** se configura automáticamente al importar módulos. Para silenciar en scripts, configura antes de importar licit.
5. **subprocess calls** (git) tienen timeouts — no se quedan colgados.
