# Guía enterprise

Guía para organizaciones que evalúan o adoptan licit como parte de su estrategia de gobernanza de IA.

---

## Para quién es esta guía

- **CTOs / VP Engineering**: Evaluando herramientas de AI governance
- **Compliance officers**: Necesitan documentación regulatoria automatizada
- **Legal teams**: Preparando para auditorías EU AI Act
- **Security leads**: Implementando controles OWASP para agentes IA
- **Procurement**: Evaluando licit vs alternativas

---

## Propuesta de valor

### El problema

Las organizaciones que usan agentes IA para generar código enfrentan tres brechas:

1. **Trazabilidad**: No pueden distinguir código humano de código IA a escala. Esto crea riesgos de propiedad intelectual, responsabilidad legal, y gestión de calidad.

2. **Regulación**: El EU AI Act exige documentación específica (FRIA, Annex IV), sistemas de gestión de riesgos, y supervisión humana. Generar esta documentación manualmente es costoso y propenso a errores.

3. **Seguridad de agentes**: Los agentes IA operan con permisos elevados y pueden introducir vulnerabilidades que las herramientas de seguridad tradicionales no cubren (OWASP Agentic Top 10).

### Cómo licit lo resuelve

| Capacidad | Beneficio enterprise |
|---|---|
| Provenance tracking | Trazabilidad auditable de código AI vs humano |
| FRIA generator | Documentación regulatoria Art. 27 automatizada |
| Annex IV generator | Documentación técnica auto-poblada desde metadatos |
| EU AI Act evaluator | Evaluación artículo-por-artículo con evidencia |
| OWASP evaluator | Postura de seguridad contra 10 riesgos agentic |
| Gap analyzer | Brechas priorizadas con recomendaciones accionables |
| CI/CD gate | Compliance integrado en el pipeline de desarrollo |
| Config changelog | Auditoría de cambios en configuración de agentes |

### Diferenciadores clave

1. **Standalone**: No requiere SaaS, bases de datos, ni infraestructura. Todo son archivos locales.
2. **Developer-first**: CLI que se integra en git/CI/CD workflows existentes.
3. **Agnóstico de lenguaje**: Python, JS/TS, Go, Rust, Java.
4. **Open source (MIT)**: Sin vendor lock-in, auditable, extensible.
5. **Multi-framework**: EU AI Act + OWASP en una ejecución, con NIST/ISO en roadmap.

---

## Modelo de adopción

### Fase 1: Piloto (1-2 semanas)

**Objetivo**: Validar licit en un proyecto representativo.

```bash
# Un dev instala y prueba
pip install licit-ai-cli
cd proyecto-piloto/
licit init
licit trace --stats
licit report --format html -o compliance.html
licit gaps
```

**Entregable**: Reporte HTML de compliance + gap analysis del proyecto piloto.

### Fase 2: Equipo (2-4 semanas)

**Objetivo**: Integrar en el flujo de CI/CD de un equipo.

1. Añadir `licit verify` al pipeline de PRs
2. Completar el FRIA (`licit fria`)
3. Generar Annex IV (`licit annex-iv`)
4. Habilitar connectors si usan architect/vigil
5. Versionar `.licit.yaml` y reportes

### Fase 3: Organización (1-3 meses)

**Objetivo**: Estandarizar compliance de IA en toda la organización.

1. Definir `.licit.yaml` estándar por tipo de proyecto
2. Configurar dashboards (parseando JSON reports)
3. Integrar en proceso de auditoría interna
4. Designar compliance leads por equipo
5. Establecer cadencia de revisión (mensual/quarterly)

---

## Requisitos técnicos

| Requisito | Detalle |
|---|---|
| **Runtime** | Python 3.12+ |
| **Dependencias** | 6 paquetes PyPI (click, pydantic, structlog, pyyaml, jinja2, cryptography) |
| **Almacenamiento** | ~50 MB por proyecto (provenance store + reportes) |
| **Red** | No requiere. Funciona 100% offline/air-gapped. |
| **Permisos** | Solo lectura del proyecto + escritura en `.licit/` |
| **CI/CD** | GitHub Actions, GitLab CI, Jenkins (templates incluidos) |
| **Git** | Requiere historial git para provenance tracking |

---

## Marcos regulatorios cubiertos

### EU AI Act — Cobertura actual

| Obligación | Artículo | Estado licit |
|---|---|---|
| Sistema de gestión de riesgos | Art. 9 | Evaluado (guardrails, quality gates, scanning) |
| Gobernanza de datos | Art. 10 | Evaluado (perspectiva deployer) |
| Logging automático | Art. 12 | Evaluado (git, audit trail, provenance) |
| Transparencia | Art. 13 | Evaluado (Annex IV, changelog) |
| Supervisión humana | Art. 14 | Evaluado (review gates, dry-run, rollback) |
| Obligaciones de deployer | Art. 26 | Evaluado (agent configs, monitoring) |
| Evaluación de impacto (FRIA) | Art. 27 | Generador interactivo + modo `--auto` para CI/CD |
| Documentación técnica | Annex IV | Generador auto-poblado desde metadatos |

### OWASP Agentic Top 10 — Cobertura actual

Los 10 riesgos evaluados cubren: control de acceso, inyección de prompts, cadena de suministro, logging, manejo de output, supervisión humana, sandboxing, consumo de recursos, manejo de errores, y exposición de datos.

### Roadmap de frameworks

| Marco | Versión licit | Estado |
|---|---|---|
| EU AI Act | V0 (actual) | Implementado |
| OWASP Agentic Top 10 | V0 (actual) | Implementado |
| NIST AI RMF | V1 | Planificado |
| ISO/IEC 42001 | V1 | Planificado |
| SOC 2 AI Controls | V2 | Bajo evaluación |

---

## Seguridad y datos

### Qué datos genera licit

| Dato | Sensibilidad | Recomendación |
|---|---|---|
| Provenance store (JSONL) | Media (nombres de contributors) | No versionar en repos públicos |
| FRIA data (JSON) | Alta (evaluación de derechos) | No versionar; almacenar en sistema seguro |
| Reportes de compliance | Baja (metadata, no código) | Versionar; compartir con auditoría |
| Annex IV | Baja (documentación técnica) | Versionar |
| Config changelog | Baja (cambios en configs) | Versionar |
| Signing key | Crítica | Nunca versionar; permisos 600 |

### Modelo de seguridad

- **Sin red**: licit no hace HTTP requests, no tiene telemetría, no phone-home
- **Read-only**: Los connectors solo leen; nunca modifican código fuente
- **Sin ejecución**: No compila, interpreta, ni ejecuta código analizado
- **YAML seguro**: Solo usa `yaml.safe_load()` (sin ejecución de código)
- **Firmado**: HMAC-SHA256 opcional para integridad de provenance

---

## Integración con herramientas existentes

### Herramientas de seguridad

| Herramienta | Integración con licit | Cómo |
|---|---|---|
| **vigil** | Connector nativo | `licit connect vigil` — lee SARIF |
| **Semgrep** | Via SARIF | Generar `.sarif` y configurar `sarif_path` |
| **Snyk** | Detección automática | `ProjectDetector` detecta `.snyk` |
| **CodeQL** | Detección automática | Detecta `.github/codeql/` |
| **Trivy** | Detección automática | Detecta config de Trivy |

### Herramientas de IA

| Herramienta | Integración con licit | Cómo |
|---|---|---|
| **Claude Code** | Session reader + git heuristics | Provenance tracking automático |
| **Cursor** | Git heuristics + config monitoring | `.cursorrules` tracking |
| **GitHub Copilot** | Git heuristics + config monitoring | `.github/copilot-instructions.md` |
| **architect** | Connector nativo | `licit connect architect` — lee reports/audit/config |
| **GitHub Agents** | Config monitoring | `AGENTS.md` tracking |

### Plataformas GRC (Governance, Risk, Compliance)

licit genera reportes JSON que pueden alimentar plataformas GRC:

```bash
licit report --format json -o compliance-data.json
# → Parsear con la API de tu plataforma GRC
```

El JSON contiene: project metadata, per-framework results, compliance rates, gap analysis.

---

## Preguntas frecuentes enterprise

### ¿licit reemplaza una auditoría?

**No.** licit automatiza la recopilación de evidencia técnica y genera documentación regulatoria. Las decisiones finales de compliance deben ser revisadas por profesionales cualificados. licit es una herramienta para el auditor, no un sustituto del auditor.

### ¿El reporte de licit es legalmente vinculante?

**No.** Los reportes de licit son evidencia técnica de soporte. Para obligaciones legales del EU AI Act, se requiere revisión legal formal del FRIA y la documentación técnica.

### ¿Funciona en entornos air-gapped?

**Sí.** licit no requiere conexión a internet en ningún momento. Solo necesita Python 3.12 y sus 6 dependencias instaladas previamente.

### ¿Soporta monorepos?

licit analiza un directorio raíz. Para monorepos, ejecuta `licit init` en cada subdirectorio de proyecto o en la raíz según tu necesidad.

### ¿Cuál es el coste de ejecución en CI/CD?

`licit verify` típicamente toma 2-5 segundos en proyectos medianos (100-500 commits). `licit trace` puede tomar 10-30 segundos en repos grandes (10,000+ commits). No requiere servicios externos ni API calls.

### ¿Cómo manejan la propiedad intelectual del código generado por IA?

licit no toma posición legal sobre IP. Lo que hace es **rastrear** qué código fue generado por IA (y por qué modelo), lo cual es evidencia necesaria para cualquier análisis de IP que tu equipo legal necesite hacer.

---

## Soporte y comunidad

- **Issues**: [github.com/Diego303/licit-cli/issues](https://github.com/Diego303/licit-cli/issues)
- **Documentación**: [docs/](.)
- **Licencia**: MIT (uso comercial permitido sin restricciones)
- **Seguridad**: [SECURITY.md](../SECURITY.md)
