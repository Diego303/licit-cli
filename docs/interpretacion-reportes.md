# Interpretación de reportes

## Formatos disponibles

```bash
licit report                              # Markdown (default)
licit report --format json -o report.json # JSON estructurado
licit report --format html -o report.html # HTML auto-contenido
```

Los tres formatos contienen la misma información; solo cambia la presentación.

---

## Estructura del reporte

Todo reporte tiene tres niveles:

```
1. Overall Summary    →  Estadísticas agregadas de todos los frameworks
2. Per-framework      →  Resumen + detalle para cada framework evaluado
3. Per-requirement    →  Status, evidencia y recomendaciones por requisito
```

---

## 1. Resumen overall

```
  Overall: [####................] 19.0%
  4/21 controls compliant
```

| Campo | Significado |
|---|---|
| Compliance rate | `compliant / (compliant + partial + non_compliant) * 100`. No incluye N/A ni not-evaluated |
| Total controls | EU AI Act (11) + OWASP Agentic (10) = 21 controles |
| Compliant | Requisitos con evidencia suficiente |
| Partial | Evidencia parcial — mejoras posibles |
| Non-compliant | Sin evidencia — acción requerida |

### Cómo interpretar la tasa

| Rango | Interpretación | Acción |
|---|---|---|
| 80-100% | Postura de compliance sólida | Mantener y monitorear |
| 50-79% | Compliance parcial, brechas manejables | Cerrar gaps prioritarios con `licit gaps` |
| 20-49% | Compliance débil | Plan de remediación urgente |
| 0-19% | Compliance mínimo — típico de proyecto recién inicializado | Ejecutar `licit fria`, `licit annex-iv`, `licit trace` |

> **Un proyecto nuevo sin FRIA ni Annex IV empezará con ~5-20%.** Esto es normal. Cada comando de licit que ejecutas sube la tasa.

---

## 2. Sección por framework

### EU AI Act

```
  eu-ai-act (2024/1689)
    [##..................] 9.1%
    1 compliant | 4 partial | 6 non-compliant
```

Los 11 artículos evaluados cubren obligaciones del **deployer** (quien usa el sistema de IA), no del provider (quien lo fabrica):

| Artículo | Qué evalúa | Cómo subir el score |
|---|---|---|
| Art. 9 | Gestión de riesgos | Configurar guardrails en architect, añadir vigil/semgrep |
| Art. 10 | Gobernanza de datos | Siempre PARTIAL (deployer no entrena) — documentar prácticas del provider |
| Art. 12 | Registro automático | `licit trace` para provenance, habilitar audit trail |
| Art. 13 | Transparencia | `licit annex-iv` + `licit changelog` |
| Art. 14 | Supervisión humana | Configurar PR reviews, architect dry-run |
| Art. 26 | Obligaciones deployer | Tener configs de agentes (CLAUDE.md, .cursorrules) |
| Art. 27 | FRIA | `licit fria` |
| Annex IV | Doc. técnica | `licit annex-iv` |

### OWASP Agentic Top 10

```
  owasp-agentic (2025)
    [....................] 0.0%
    0 compliant | 5 partial | 5 non-compliant
```

Los 10 riesgos evalúan la **postura de seguridad** para agentes de IA:

| Riesgo | Qué evalúa | Cómo subir el score |
|---|---|---|
| ASI01 | Permisos excesivos | Guardrails, quality gates, budget limits |
| ASI02 | Inyección de prompt | vigil scanning, guardrails de input |
| ASI03 | Supply chain | Snyk/Semgrep/CodeQL, changelog de configs |
| ASI04 | Logging insuficiente | `licit trace`, audit trail, OTel |
| ASI05 | Output sin validar | Human review gates, quality gates, test suite |
| ASI06 | Sin supervisión humana | PR reviews, dry-run, rollback |
| ASI07 | Sandboxing débil | Guardrails, CI/CD isolation |
| ASI08 | Consumo sin límites | Budget limits en architect |
| ASI09 | Error handling pobre | Test suite, CI/CD, rollback |
| ASI10 | Exposición de datos | Protected files, security scanning |

---

## 3. Detalle por requisito

Cada requisito muestra:

### En Markdown

```markdown
### [FAIL] ART-27-1: Fundamental Rights Impact Assessment (FRIA)

- **Status**: non-compliant
- **Reference**: Article 27(1)
- **Evidence**: No FRIA document found

**Recommendations:**
- Run: licit fria -- to complete the Fundamental Rights Impact Assessment
```

### En JSON

```json
{
  "id": "ART-27-1",
  "name": "Fundamental Rights Impact Assessment (FRIA)",
  "status": "non-compliant",
  "evidence": "No FRIA document found",
  "recommendations": [
    "Run: licit fria -- to complete the Fundamental Rights Impact Assessment"
  ]
}
```

### En HTML

Status con badge de color: verde (compliant), ámbar (partial), rojo (non-compliant), gris (n/a).

---

## Gap analysis

```bash
licit gaps
```

Los gaps son un subconjunto del reporte: solo muestran requisitos `non-compliant` y `partial`, ordenados por severidad.

### Cómo leer un gap

```
  1. [X] [ART-27-1] Fundamental Rights Impact Assessment (FRIA)
     Missing: Before putting an AI system into use...
     -> Run: licit fria -- to complete the FRIA
     Tools: licit fria
```

| Elemento | Significado |
|---|---|
| `[X]` | Non-compliant (prioridad alta). `[!]` = partial |
| `[ART-27-1]` | ID del requisito |
| `Missing:` | No hay evidencia. `Incomplete:` = evidencia parcial |
| `->` | Recomendación concreta |
| `Tools:` | Herramientas específicas que ayudan |

### Estrategia de remediación

1. **Primero los `[X]` (non-compliant)** — son los que harían fallar `licit verify` en CI/CD
2. **Dentro de `[X]`, los de effort "low" primero** — ganancias rápidas
3. **Los `[!]` (partial) después** — mejoran la tasa pero no bloquean el pipeline

### Esfuerzo estimado

Cada gap tiene un effort implícito por categoría:

| Effort | Tiempo típico | Ejemplo |
|---|---|---|
| low | <1 hora | Ejecutar `licit trace`, `licit annex-iv`, `licit changelog` |
| medium | 1-4 horas | Completar `licit fria`, configurar guardrails, añadir PR reviews |
| high | 1-3 días | Configurar vigil/semgrep, implementar sandboxing, configurar budget limits |

---

## Configuración de reportes

En `.licit.yaml`:

```yaml
reports:
  output_dir: .licit/reports        # Dónde se guardan
  default_format: markdown          # Formato por defecto
  include_evidence: true            # Incluir campo Evidence en cada requisito
  include_recommendations: true     # Incluir recomendaciones
```

### Sin evidencia

Con `include_evidence: false`, los reportes omiten la línea de evidencia. Útil para reportes ejecutivos que solo necesitan el status.

### Sin recomendaciones

Con `include_recommendations: false`, se omiten las recomendaciones. Útil si ya las conoces y solo quieres el snapshot de status.

---

## Comparar reportes en el tiempo

Genera reportes JSON periódicamente y compara:

```bash
# Semana 1
licit report --format json -o report-w1.json

# Semana 2
licit report --format json -o report-w2.json

# Comparar manualmente
diff <(jq '.overall' report-w1.json) <(jq '.overall' report-w2.json)
```

Ejemplo de mejora:

```diff
-  "compliance_rate": 4.8
+  "compliance_rate": 33.3
-  "non_compliant": 11
+  "non_compliant": 5
```

> En versiones futuras, `licit diff` automatizará esta comparación.
