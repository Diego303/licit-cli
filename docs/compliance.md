# Compliance y marcos regulatorios

## Por qué compliance en desarrollo con IA

El uso de agentes IA en desarrollo de software introduce riesgos regulatorios específicos:

- **Trazabilidad**: ¿Quién escribió cada línea de código? ¿Un humano o una IA?
- **Gobernanza**: ¿Cómo se configuran y controlan los agentes IA?
- **Transparencia**: ¿Se documenta adecuadamente el uso de IA?
- **Seguridad**: ¿Existen guardrails para prevenir comportamiento no deseado?
- **Responsabilidad**: ¿Hay revisión humana antes de desplegar código generado por IA?

licit evalúa estos aspectos contra marcos regulatorios establecidos.

---

## EU AI Act (Reglamento UE 2024/1689)

### Alcance

El EU AI Act es el primer marco regulatorio integral para inteligencia artificial. Entró en vigor en agosto de 2024, con aplicación gradual hasta agosto de 2027.

licit evalúa los artículos relevantes para **equipos de desarrollo que usan agentes IA**:

### Artículos evaluados

| Artículo | Nombre | Qué evalúa licit |
|---|---|---|
| Art. 9(1) | Sistema de gestión de riesgos | Guardrails, quality gates, budget limits, security scanning |
| Art. 10(1) | Datos y gobernanza de datos | Perspectiva deployer — documentar prácticas del proveedor |
| Art. 12(1) | Record keeping — logging automático | Git history, audit trail, provenance tracking, OTel |
| Art. 13(1) | Transparencia | Annex IV, changelog de configs, trazabilidad de requisitos |
| Art. 14(1) | Supervisión humana | Dry-run, human review gate, quality gates, budget limits |
| Art. 14(4)(a) | Oversight — entender capacidades | Misma evidencia que Art. 14(1) |
| Art. 14(4)(d) | Oversight — capacidad de intervenir | Dry-run + rollback |
| Art. 26(1) | Deployer — uso conforme | Configs de agentes presentes |
| Art. 26(5) | Deployer — monitoreo | Misma evidencia que Art. 12(1) |
| Art. 27(1) | FRIA | Documento FRIA completado |
| Annex IV | Documentación técnica | Documento Annex IV generado |

### Scoring del evaluador

Cada artículo tiene un método de evaluación dedicado con scoring numérico. El score se convierte a status con `_score_to_status(score, compliant_at, partial_at)`:

| Artículo | Indicadores (score) | Compliant at | Partial at |
|---|---|---|---|
| Art. 9 | Guardrails +1, quality gates +1, budget +1, scanning +1 | 3+ | 1+ |
| Art. 10 | Siempre PARTIAL (deployer no entrena) | — | — |
| Art. 12 | Git +1, audit trail +2, provenance +1, OTel +1 | 3+ | 1+ |
| Art. 13 | Annex IV +2, changelog +1, traceability +1 | 2+ | 1+ |
| Art. 14 | Dry-run +1, review gate +2, quality gates +1, budget +1 | 3+ | 1+ |

El evaluador genera recomendaciones accionables con comandos licit concretos (ej: "Run: licit trace -- to start tracking code provenance").

### FRIA — Evaluación de Impacto en Derechos Fundamentales

El FRIA (Fundamental Rights Impact Assessment) es obligatorio para sistemas de IA de alto riesgo según el Art. 27. licit genera un FRIA interactivo en 5 pasos con 16 preguntas y auto-detección de 8 campos:

1. **System Description** (5 preguntas): Propósito, tecnología AI, modelos, alcance, revisión humana.
2. **Fundamental Rights Identification** (4 preguntas): Datos personales, empleo, seguridad, discriminación.
3. **Impact Assessment** (3 preguntas): Nivel de riesgo, impacto máximo, velocidad de detección.
4. **Mitigation Measures** (5 preguntas): Guardrails, scanning, testing, audit trail, medidas adicionales.
5. **Monitoring & Review** (3 preguntas): Frecuencia de revisión, responsable, proceso de incidentes.

**Auto-detección:** Para campos como `system_purpose`, `guardrails`, `security_scanning`, `testing`, y `audit_trail`, licit infiere la respuesta desde el `ProjectContext` y `EvidenceBundle` del proyecto.

**Comando:**
```bash
licit fria            # Cuestionario interactivo nuevo
licit fria --update   # Actualizar FRIA existente
```

**Archivos generados:**
- `.licit/fria-data.json` — Datos raw (JSON, reutilizable con `--update`)
- `.licit/fria-report.md` — Reporte Markdown con template Jinja2

### Annex IV — Documentación Técnica

El Anexo IV define la documentación técnica requerida para sistemas de IA. licit genera esta documentación auto-poblándola desde 27 variables de template extraídas de:

- Metadatos del proyecto (`pyproject.toml`, `package.json`)
- Configuración de CI/CD
- Configuraciones de agentes IA
- Frameworks de testing y herramientas de seguridad
- Datos de provenance (% código AI)
- Evidencia de guardrails, quality gates, budget limits, FRIA, audit trail

**6 secciones auto-generadas:**
1. General Description — Propósito, componentes AI, lenguajes, frameworks
2. Development Process — Version control, provenance, configs de agentes
3. Monitoring & Control — CI/CD, audit trail, changelog
4. Risk Management — Guardrails, quality gates, budget, oversight, FRIA
5. Testing & Validation — Test framework, security scanning
6. Changes & Lifecycle — Mecanismos de tracking

Cada sección sin evidencia genera una **recomendación accionable** (ej: "Run `licit trace` to begin tracking code provenance").

**Comando:**
```bash
licit annex-iv --organization "Mi Empresa" --product "Mi Producto"
```

---

## OWASP Agentic Top 10

### Alcance

El OWASP Agentic Top 10 identifica los 10 principales riesgos de seguridad en aplicaciones que usan agentes IA. licit evalúa la postura del proyecto contra cada riesgo.

### Riesgos evaluados

| ID | Riesgo | Qué evalúa licit |
|---|---|---|
| ASI-01 | Excessive Agency | Guardrails, archivos protegidos, comandos bloqueados |
| ASI-02 | Uncontrolled Autonomy | Límites de presupuesto, dry-run, aprobación humana |
| ASI-03 | Supply Chain Vulnerabilities | Herramientas de seguridad (Semgrep, Snyk, etc.) |
| ASI-04 | Improper Output Handling | Validación de outputs, quality gates |
| ASI-05 | Insecure Communication | Configuración de conectores, protección de datos |
| ASI-06 | Insufficient Monitoring | Audit trail, logging, OpenTelemetry |
| ASI-07 | Identity and Access Mismanagement | Permisos de agentes, scope de acceso |
| ASI-08 | Inadequate Sandboxing | Aislamiento de ejecución, rollback capability |
| ASI-09 | Prompt Injection | Validación de inputs, configuración de guardrails |
| ASI-10 | Insufficient Logging | Logs estructurados, trazabilidad de sesiones |

### Mapeo a evidencia

Cada riesgo OWASP se mapea a evidencia recopilable:

```
ASI-01 (Excessive Agency)
  ├── has_guardrails → ¿Hay guardrails configurados?
  ├── guardrail_count → ¿Cuántos controles existen?
  └── has_human_review_gate → ¿Hay revisión humana?

ASI-02 (Uncontrolled Autonomy)
  ├── has_budget_limits → ¿Hay límites de presupuesto?
  ├── has_dry_run → ¿Existe modo dry-run?
  └── has_rollback → ¿Hay capacidad de rollback?

ASI-06 (Insufficient Monitoring)
  ├── has_audit_trail → ¿Hay trail de auditoría?
  ├── audit_entry_count → ¿Cuántas entradas?
  └── has_otel → ¿Hay instrumentación OpenTelemetry?
```

---

## Cómo evalúa licit el compliance

### Proceso de evaluación

```
1. Detectar    → ProjectDetector analiza el proyecto
2. Recopilar   → EvidenceCollector reúne evidencia
3. Evaluar     → Evaluadores aplican requisitos del marco
4. Clasificar  → Cada requisito: compliant / partial / non-compliant / n/a
5. Reportar    → Reporte con evidencia, brechas y recomendaciones
```

### Fuentes de evidencia

| Fuente | Qué aporta | Estado |
|---|---|---|
| Git history | Proveniencia del código, contribuidores, frecuencia | **Funcional** (v0.2.0) |
| Session logs | Logs de sesión de agentes IA (Claude Code) | **Funcional** (v0.2.0) |
| Agent config changelog | Cambios en configs de agentes con severidad | **Funcional** (v0.3.0) |
| Agent configs | Guardrails, modelos usados, reglas de código | **Funcional** (v0.1.0) |
| CI/CD configs | Human review gates, steps de seguridad | **Funcional** (v0.1.0) |
| Architect reports | Audit trail, calidad de ejecución | Fase 7 |
| SARIF files | Hallazgos de seguridad (vulnerabilidades) | Fase 7 |
| `.licit/` data | FRIA, Annex IV, changelog, provenance store | **Funcional** (v0.4.0 — todos los generadores operativos) |

La evidencia de provenance (`licit trace`) alimenta directamente los artículos de transparencia (Art. 13) y trazabilidad (Art. 10) del EU AI Act. El changelog de configs (`licit changelog`) alimenta los artículos de transparencia (Art. 13) y obligaciones de deployers (Art. 26). Ambos alimentan los controles de monitoring (ASI-06, ASI-10) del OWASP Agentic Top 10.

### Niveles de cumplimiento

| Estado | Significado | Acción requerida |
|---|---|---|
| `compliant` | Requisito totalmente cumplido | Ninguna |
| `partial` | Requisito parcialmente cumplido | Mejorar evidencia o controles |
| `non-compliant` | Requisito no cumplido | Implementar controles faltantes |
| `n/a` | No aplica al proyecto | Ninguna |
| `not-evaluated` | Aún no evaluado | Ejecutar evaluación |

---

## Reportes de compliance

### Formatos disponibles

| Formato | Uso recomendado |
|---|---|
| **Markdown** | Revisión humana, PRs, documentación |
| **JSON** | Integración con otras herramientas, dashboards |
| **HTML** | Presentación a stakeholders, auditorías |

### Estructura del reporte

```markdown
# Compliance Report — Mi Proyecto
Generated: 2026-03-10

## Summary
- EU AI Act: 72% compliant (13/18 controls)
- OWASP Agentic: 60% compliant (6/10 controls)

## EU AI Act
### Article 9 — Risk Management
Status: PARTIAL
Evidence: FRIA exists but incomplete
Recommendation: Complete FRIA sections 3-5

### Article 14 — Human Oversight
Status: COMPLIANT
Evidence: GitHub Actions requires approval for deployment
...

## Gaps
| Priority | Requirement | Gap | Effort |
|---|---|---|---|
| 1 | ART-9-1 | No risk assessment | Medium |
| 2 | ASI-01 | No guardrails | Low |
```

---

## CI/CD Gate

licit puede actuar como gate de compliance en pipelines de CI/CD:

```yaml
# .github/workflows/compliance.yml
name: Compliance Check
on: [push, pull_request]

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # Necesario para análisis git

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install licit
        run: pip install licit-ai-cli

      - name: Run compliance check
        run: licit verify
        # Exit 0 = pass, Exit 1 = fail, Exit 2 = warnings
```

**Códigos de salida:**

| Código | Resultado | Pipeline |
|---|---|---|
| 0 | Todos los requisitos críticos cumplidos | Pass |
| 1 | Algún requisito crítico no cumplido | Fail |
| 2 | Algún requisito parcialmente cumplido | Warning (configurable) |

---

## Marcos futuros (V1+)

licit está diseñado para soportar marcos adicionales:

| Marco | Estado | Descripción |
|---|---|---|
| **NIST AI RMF** | Planificado (V1) | Risk Management Framework del NIST |
| **ISO/IEC 42001** | Planificado (V1) | Sistema de gestión de IA |
| **SOC 2 AI** | Considerado | Controles SOC 2 específicos de IA |
| **IEEE 7000** | Considerado | Diseño ético de sistemas |

La arquitectura de `frameworks/` permite añadir nuevos marcos implementando un evaluador con la interfaz Protocol correspondiente.
