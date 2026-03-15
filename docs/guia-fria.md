# Guía para completar el FRIA

## Qué es el FRIA

El FRIA (Fundamental Rights Impact Assessment) es una evaluación obligatoria bajo el **Artículo 27 del EU AI Act**. Antes de poner en uso un sistema de IA, el deployer debe evaluar su impacto en derechos fundamentales.

licit genera el FRIA mediante un cuestionario interactivo de 5 pasos con 16 preguntas. Varias respuestas se auto-detectan desde la configuración del proyecto.

```bash
licit fria             # Iniciar nuevo FRIA
licit fria --update    # Actualizar FRIA existente
```

---

## Los 5 pasos

### Paso 1 — Descripción del sistema

> **Objetivo:** Documentar qué es el sistema de IA, qué hace, y cómo se despliega.

#### 1.1 — ¿Cuál es el propósito principal de este sistema de IA?

Describe lo que hace el sistema en una o dos frases concretas.

| Tipo de respuesta | Ejemplo |
|---|---|
| Buena | "Generación autónoma de código y modificación de archivos en pipelines CI/CD usando Claude Code" |
| Buena | "Asistente interactivo de código para desarrolladores usando Cursor con Claude Sonnet 4" |
| Mala | "Usar IA" |
| Mala | "Desarrollo" |

**Auto-detección:** licit infiere el propósito desde las configs de agentes detectadas (CLAUDE.md, .cursorrules, etc.).

#### 1.2 — ¿Qué tipo de tecnología de IA se usa?

| Opción | Cuándo seleccionar |
|---|---|
| LLM for code generation | El agente genera código pero un humano lo revisa y ejecuta |
| AI coding assistant (interactive) | El desarrollador trabaja junto al agente (Cursor, Copilot) |
| Autonomous AI agent (headless) | El agente opera sin intervención humana (Claude Code en CI, architect) |
| Multi-agent system | Varios agentes colaboran (architect + vigil, o custom) |

**Auto-detección:** licit detecta si hay architect (headless) o solo configs interactivas (Cursor, Copilot).

#### 1.3 — ¿Qué modelos/proveedores de IA se usan?

Lista los modelos concretos. Los reguladores quieren saber qué modelos están en uso.

| Tipo de respuesta | Ejemplo |
|---|---|
| Buena | "Claude Sonnet 4 (Anthropic) para generación de código, GPT-4.1 (OpenAI) para revisión" |
| Buena | "Claude Opus 4 (Anthropic) via Claude Code" |
| Mala | "IA" |

**Auto-detección:** licit lee la config de architect para detectar el modelo configurado.

#### 1.4 — ¿Cuántas personas/sistemas se ven afectados?

Esto determina el **alcance de impacto**:

| Opción | Implicación regulatoria |
|---|---|
| Internal team (<50) | Riesgo bajo — impacto limitado a desarrolladores |
| Internal org (50-500) | Riesgo medio — el software producido afecta a la organización |
| External users (500-10K) | Riesgo alto — usuarios finales dependen del software producido |
| Large-scale (10K+) | Riesgo muy alto — justifica medidas de mitigación exhaustivas |

#### 1.5 — ¿Se requiere revisión humana?

| Opción | Lo que implica para compliance |
|---|---|
| Sí, toda | Art. 14 compliance fuerte. Documenta el proceso de review |
| Parcialmente | Documenta qué se revisa y qué no, y por qué |
| No | Alto riesgo. Debes justificar por qué es aceptable y qué mitigaciones alternativas hay |

**Auto-detección:** licit verifica si hay CI/CD con GitHub Actions (implica PR reviews) o architect con dry-run.

---

### Paso 2 — Identificación de derechos fundamentales

> **Objetivo:** Identificar qué derechos fundamentales podrían verse afectados por el sistema de IA.

#### 2.1 — ¿El sistema procesa datos personales?

Considerar si el código fuente o las configuraciones contienen:
- Nombres de personas en comentarios o git history
- Direcciones de email en configs
- Tokens/credenciales (aunque no deberían estar ahí)

| Opción | Cuándo |
|---|---|
| Sí | El código maneja datos de usuarios (formularios, bases de datos, APIs con PII) |
| No | Código de infraestructura, librerías, herramientas internas sin datos de usuarios |
| Possibly | No está claro — el agente IA podría generar código que procese datos |

#### 2.2 — ¿Podría afectar empleo o condiciones laborales?

| Opción | Cuándo |
|---|---|
| No — solo genera código | El output del agente es código revisado por humanos |
| Posiblemente — métricas de productividad | Si se usan métricas de código IA para evaluar rendimiento de desarrolladores |
| Sí — decisiones de contratación | Si el sistema influye en decisiones de RRHH |

#### 2.3 — ¿Vulnerabilidades podrían afectar derechos de usuarios?

| Opción | Cuándo |
|---|---|
| Low risk — internal tools | El software producido es de uso interno exclusivo |
| Medium risk — user-facing | El software tiene usuarios pero no maneja datos críticos |
| High risk — financial/health/identity | El software maneja dinero, salud, o identidad de personas |

#### 2.4 — ¿Podría introducir comportamiento discriminatorio?

| Opción | Cuándo |
|---|---|
| No — backend/infra | El código es puramente técnico |
| Posiblemente | El código interactúa con decisiones que afectan personas (recomendaciones, filtros) |
| Sí | El código implementa algoritmos de decisión (scoring, clasificación, selección) |

---

### Paso 3 — Evaluación de impacto

> **Objetivo:** Evaluar la probabilidad y severidad del impacto en los derechos identificados.

#### 3.1 — Nivel de riesgo general

| Opción | Criterio |
|---|---|
| Minimal | Herramienta de desarrollo con supervisión humana completa |
| Limited | Alguna automatización pero con gates de revisión |
| High | Operación autónoma con supervisión limitada |
| Unacceptable | Completamente autónomo sin salvaguardas — **no es aceptable bajo el EU AI Act** |

> Si seleccionas "Unacceptable", debes implementar salvaguardas antes de proceder.

#### 3.2 — Impacto máximo potencial

Describe el peor escenario realista. Los reguladores quieren ver que has pensado en esto.

| Tipo de respuesta | Ejemplo |
|---|---|
| Buena | "Vulnerabilidad de seguridad en código generado podría exponer datos de 10K usuarios. Impacto financiero estimado: 50K-200K EUR. Tiempo de detección: <24h via CI/CD" |
| Mala | "Nada malo puede pasar" |

#### 3.3 — Velocidad de detección y reversión

| Opción | Implicación |
|---|---|
| Immediately — automated tests | Fuerte. Documenta tu test suite y coverage |
| Hours — CI/CD | Aceptable. Documenta tu pipeline |
| Days — manual review | Débil. Considera automatizar |
| Unknown | Inaceptable. Implementa detección antes de continuar |

---

### Paso 4 — Medidas de mitigación

> **Objetivo:** Documentar las medidas existentes y planificadas para mitigar riesgos.

#### 4.1 — Guardrails

**Auto-detección:** licit lee la config de architect para detectar guardrails.

Documenta qué restricciones tiene el agente IA:

| Medida | Ejemplo |
|---|---|
| Protected files | `README.md`, `.env`, `Dockerfile` — el agente no puede modificarlos |
| Blocked commands | `rm -rf /`, `DROP TABLE`, `curl | sh` — comandos prohibidos |
| Budget limits | Máximo $5 USD por ejecución |
| Quality gates | Tests deben pasar antes de commit |

#### 4.2 — Security scanning

**Auto-detección:** licit detecta vigil, semgrep, snyk, codeql, trivy.

#### 4.3 — Testing

**Auto-detección:** licit detecta pytest, jest, vitest, go test.

#### 4.4 — Audit trail

**Auto-detección:** licit verifica si existe `.licit/provenance.jsonl` y `.architect/reports/`.

#### 4.5 — Medidas adicionales

Campo libre para medidas no cubiertas por las preguntas anteriores. Ejemplos:
- "Revisión de código por dos desarrolladores senior antes de merge"
- "Entrenamiento trimestral del equipo sobre riesgos de IA"
- "Seguro de responsabilidad civil para productos de software"

---

### Paso 5 — Monitoreo y revisión

> **Objetivo:** Definir procesos de monitoreo continuo y revisión periódica.

#### 5.1 — Frecuencia de revisión

| Opción | Cuándo es apropiado |
|---|---|
| Quarterly | Riesgo alto, cambios frecuentes en el sistema |
| Semi-annually | Riesgo medio, sistema estable |
| Annually | Riesgo bajo, sin cambios significativos |
| On significant changes | Cuando cambia el modelo, el scope, o los guardrails |

> **Recomendación:** combinar "On significant changes" con una frecuencia mínima (al menos anual).

#### 5.2 — Responsable de compliance

Designa una persona concreta con nombre y rol. Los reguladores quieren un punto de contacto.

#### 5.3 — Proceso de incidentes

Describe qué pasa cuando el código generado por IA causa un problema:
1. ¿Cómo se detecta?
2. ¿Quién es notificado?
3. ¿Cómo se revierte?
4. ¿Cómo se documenta?

---

## Después de completar el FRIA

### Archivos generados

| Archivo | Contenido |
|---|---|
| `.licit/fria-data.json` | Respuestas en bruto (JSON). **No versionar** — puede contener datos sensibles |
| `.licit/fria-report.md` | Reporte formateado en Markdown. **Sí versionar** — es el documento regulatorio |

### Actualizar un FRIA existente

```bash
licit fria --update
```

Pre-carga las respuestas anteriores y permite modificarlas.

### Cuándo actualizar

- Cuando cambia el modelo de IA usado
- Cuando cambia el scope (de interno a externo)
- Cuando cambian los guardrails significativamente
- En la frecuencia definida en el paso 5.1
