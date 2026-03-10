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
| Art. 9 | Sistema de gestión de riesgos | Existencia de FRIA, análisis de riesgos documentado |
| Art. 10 | Datos y gobernanza de datos | Trazabilidad de datos de entrenamiento y proveniencia |
| Art. 11 | Documentación técnica | Existencia de documentación Annex IV |
| Art. 13 | Transparencia | Disclosure de uso de IA, provenance tracking |
| Art. 14 | Supervisión humana | Human review gates en CI/CD, guardrails |
| Art. 15 | Precisión, robustez y seguridad | Testing, herramientas de seguridad, SARIF findings |
| Art. 17 | Sistema de gestión de calidad | Quality gates, auditoría, procesos documentados |
| Art. 26 | Obligaciones de los deployers | Uso conforme, monitoreo, registro de actividades |
| Art. 27 | FRIA | Evaluación de impacto en derechos fundamentales |

### FRIA — Evaluación de Impacto en Derechos Fundamentales

El FRIA (Fundamental Rights Impact Assessment) es obligatorio para sistemas de IA de alto riesgo según el Art. 27. licit genera un FRIA interactivo en 5 pasos:

1. **Descripción del sistema**: Qué hace, para qué se usa, quiénes son los usuarios.
2. **Identificación de derechos afectados**: Qué derechos fundamentales podrían verse impactados.
3. **Evaluación de riesgos**: Probabilidad e impacto de cada riesgo.
4. **Medidas de mitigación**: Qué controles se implementan.
5. **Conclusiones y recomendaciones**: Evaluación final.

**Comando:**
```bash
licit fria
```

### Annex IV — Documentación Técnica

El Anexo IV define la documentación técnica requerida para sistemas de IA. licit genera esta documentación auto-poblándola desde:

- Metadatos del proyecto (`pyproject.toml`, `package.json`)
- Configuración de CI/CD
- Configuraciones de agentes IA
- Frameworks de testing
- Herramientas de seguridad

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

| Fuente | Qué aporta |
|---|---|
| Git history | Proveniencia del código, contribuidores, frecuencia |
| Agent configs | Guardrails, modelos usados, reglas de código |
| CI/CD configs | Human review gates, steps de seguridad |
| Architect reports | Audit trail, calidad de ejecución |
| SARIF files | Hallazgos de seguridad (vulnerabilidades) |
| `.licit/` data | FRIA, Annex IV, changelog, provenance store |

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
