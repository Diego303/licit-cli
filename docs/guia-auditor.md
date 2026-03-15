# Guía para Auditores y Compliance Officers

## Para quién es esta guía

Esta guía es para **compliance officers**, **auditores internos/externos**, y **equipos legales** que necesitan:
- Verificar que un equipo de desarrollo cumple con regulaciones al usar IA
- Entender qué evidencia genera licit y cómo interpretarla
- Preparar documentación para auditorías regulatorias
- Validar la integridad de los datos de compliance

---

## Qué evidencia genera licit

licit produce 6 tipos de evidencia documental:

| Evidencia | Archivo | Regulación cubierta | Qué demuestra |
|---|---|---|---|
| **Provenance** | `.licit/provenance.jsonl` | Art. 12, Art. 13 | Qué código fue escrito por IA vs. humanos |
| **Config changelog** | `.licit/changelog.md` | Art. 13 | Historial de cambios en configuración de agentes IA |
| **FRIA** | `.licit/fria-report.md` | Art. 27 | Evaluación de impacto en derechos fundamentales |
| **Annex IV** | `.licit/annex-iv.md` | Annex IV | Documentación técnica del sistema de IA |
| **Compliance report** | `.licit/reports/compliance-report.*` | Arts. 9-27 | Evaluación artículo por artículo con evidencia |
| **Gap analysis** | (salida terminal) | Todos | Requisitos faltantes con recomendaciones |

---

## Cómo verificar compliance

### Paso 1: Verificación rápida

```bash
cd proyecto-a-auditar
licit verify
```

El exit code indica el estado general:
- **0**: El proyecto cumple todos los requisitos evaluados
- **1**: Hay requisitos no cumplidos (ver detalle)
- **2**: Hay requisitos parcialmente cumplidos

### Paso 2: Reporte detallado

```bash
licit report --format html -o auditoria.html
```

El reporte HTML incluye:
- **Resumen overall**: tasa de compliance, controles por status
- **Evaluación por artículo**: cada requisito con status, evidencia concreta, y recomendaciones
- **Dos frameworks**: EU AI Act (11 artículos) y OWASP Agentic Top 10 (10 riesgos)

### Paso 3: Identificar brechas

```bash
licit gaps
```

Lista cada brecha con:
- `[X]` = no cumplido (prioridad alta)
- `[!]` = parcialmente cumplido
- Descripción de qué falta
- Recomendación específica de cómo resolverlo
- Herramientas sugeridas

---

## Cómo interpretar los resultados

### Estados de compliance

| Status | Significado | Acción del auditor |
|---|---|---|
| **compliant** | Evidencia suficiente de cumplimiento | Documentar como cumplido |
| **partial** | Evidencia parcial, mejoras posibles | Documentar con observaciones |
| **non-compliant** | Sin evidencia de cumplimiento | Documentar como hallazgo |
| **n/a** | No aplica al contexto del proyecto | Documentar justificación |
| **not-evaluated** | No hay evaluación automática disponible | Requiere evaluación manual |

### Tasa de compliance

```
compliance_rate = compliant / (compliant + partial + non_compliant) * 100
```

No incluye `n/a` ni `not-evaluated` en el denominador. Una tasa del 100% significa que todos los controles evaluados son compliant.

### Evidencia de provenance

El campo `evidence` en cada resultado muestra qué datos respaldaron la evaluación. Ejemplos:

| Evidence | Qué significa |
|---|---|
| "Guardrails active: 10 rules" | El proyecto tiene 10 reglas de guardrails configuradas en architect |
| "Git history: 50 commits" | licit tiene acceso al historial completo |
| "Provenance tracking: 40% AI attribution" | El 40% del código fue identificado como generado por IA |
| "No FRIA document found" | No se ha completado el FRIA |
| "FRIA completed: .licit/fria-data.json" | El FRIA existe y tiene datos |

---

## EU AI Act — Artículos evaluados

licit evalúa las obligaciones del **deployer** (quien despliega el sistema de IA), no del provider:

| Artículo | Qué verifica licit | Evidencia buscada |
|---|---|---|
| Art. 9 — Gestión de riesgos | ¿Hay guardrails, quality gates, budget limits, security scanning? | Configs de architect, vigil, semgrep, snyk |
| Art. 10 — Gobernanza de datos | Siempre PARTIAL — el deployer no entrena modelos | Nota de documentación |
| Art. 12 — Registro automático | ¿Hay git history, audit trail, provenance, OTel? | `.licit/provenance.jsonl`, `.architect/reports/` |
| Art. 13 — Transparencia | ¿Hay Annex IV, changelog, trazabilidad? | `.licit/annex-iv.md`, `.licit/changelog.md` |
| Art. 14 — Supervisión humana | ¿Hay review gates, dry-run, quality gates? | CI/CD config, architect config |
| Art. 26 — Obligaciones del deployer | ¿Hay configs de agentes? ¿Se monitorea? | CLAUDE.md, .cursorrules, etc. |
| Art. 27 — FRIA | ¿Existe el documento FRIA? | `.licit/fria-data.json` |
| Annex IV — Doc. técnica | ¿Existe documentación técnica? | `.licit/annex-iv.md` |

### Cómo mejorar una evaluación

Para mover un artículo de `non-compliant` a `compliant`:

| Artículo | Comando licit | Qué hacer |
|---|---|---|
| Art. 27 (FRIA) | `licit fria` | Completar el cuestionario interactivo de 5 pasos |
| Annex IV | `licit annex-iv` | Ejecutar — se genera automáticamente desde metadatos del proyecto |
| Art. 12 (Logging) | `licit trace` | Ejecutar análisis de provenance |
| Art. 13 (Transparencia) | `licit changelog` | Generar changelog de configs de agentes |

---

## Validación de integridad

### Provenance firmada

Si el proyecto tiene signing habilitado (`provenance.sign: true` en `.licit.yaml`), cada registro de provenance tiene una firma HMAC-SHA256. licit verifica automáticamente las firmas al cargar datos.

La clave de firma está en `.licit/.signing-key` y **no debe versionarse** en git.

### Datos append-only

El store de provenance (`.licit/provenance.jsonl`) es append-only por diseño:
- Nuevas ejecuciones de `licit trace` añaden registros, nunca borran
- Para un archivo dado, el registro más reciente prevalece
- El historial completo queda como audit trail

### Verificación manual

Para verificar que los datos de provenance son consistentes con git:

```bash
# Ver stats de provenance
licit trace --stats

# Comparar con git log real
git shortlog -sn HEAD

# Generar reporte detallado
licit trace --report
```

---

## Preparación para auditoría regulatoria

### Documentos a recopilar

1. **`.licit.yaml`** — Configuración del proyecto (qué frameworks están habilitados, qué se monitorea)
2. **`.licit/fria-report.md`** — FRIA completo (Art. 27)
3. **`.licit/annex-iv.md`** — Documentación técnica (Annex IV)
4. **`.licit/reports/compliance-report.html`** — Reporte de compliance más reciente
5. **`.licit/changelog.md`** — Historial de cambios en configs de agentes
6. **`.licit/provenance.jsonl`** — Datos crudos de trazabilidad (para verificación)

### Workflow pre-auditoría

```bash
# 1. Actualizar toda la evidencia
licit trace
licit changelog

# 2. Generar documentación regulatoria (si no existe)
licit annex-iv
# licit fria  # Solo si no se ha completado (interactivo)

# 3. Generar reporte final
licit report --format html -o auditoria-$(date +%Y%m%d).html

# 4. Revisar brechas pendientes
licit gaps
```

### Qué NO genera licit

licit **no** sustituye:
- Evaluaciones de riesgo manuales por expertos legales
- Certificaciones oficiales de organismos reguladores
- Auditorías externas por terceros acreditados
- Evaluaciones de impacto de protección de datos (DPIA bajo GDPR)

licit **sí** proporciona:
- Evidencia automatizada que respalda evaluaciones manuales
- Documentación estructurada lista para presentar a reguladores
- Monitoreo continuo de la postura de compliance

---

## Preguntas frecuentes de auditores

### ¿Cómo de precisa es la detección de código IA?

La provenance usa 6 heurísticas con un promedio ponderado. La confianza varía:
- **95%** si hay Co-authored-by con nombre de agente IA (evidencia directa)
- **60-80%** si se basa en patrones de commit (heurístico)
- **95%** si se leen logs de sesión de Claude Code (evidencia directa)

El umbral configurable (`confidence_threshold: 0.6`) determina qué se cuenta como IA.

### ¿Los reportes son alterables?

Los archivos `.md`, `.html` y `.json` son archivos planos y pueden ser editados. Para evidencia tamper-resistant:
1. Habilitar signing (`provenance.sign: true`)
2. Versionar reportes en git (el historial de git es su propia cadena de integridad)
3. Generar reportes en CI/CD (el log del pipeline es evidencia adicional)

### ¿Con qué frecuencia debo generar reportes?

| Escenario | Frecuencia recomendada |
|---|---|
| Desarrollo activo con IA | Cada sprint / cada PR (via CI/CD) |
| Preparación de release | Antes de cada release |
| Auditoría regulatoria | Al inicio de la auditoría + actualización final |
| Monitoreo continuo | Semanal (via cron en CI/CD) |
