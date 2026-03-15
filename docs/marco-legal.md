# Marco legal y regulatorio

Contexto legal de los marcos regulatorios que evalúa licit, con referencias a los textos oficiales.

---

## EU AI Act — Reglamento (UE) 2024/1689

### Contexto

El Reglamento de Inteligencia Artificial de la Unión Europea es la primera regulación integral de IA a nivel mundial. Establece reglas armonizadas para el desarrollo, la comercialización y el uso de sistemas de IA en el mercado europeo.

### Cronología de aplicación

| Fecha | Hito |
|---|---|
| Agosto 2024 | Entrada en vigor |
| Febrero 2025 | Prohibiciones de prácticas de IA (Título II) |
| Agosto 2025 | Obligaciones de modelos de propósito general (GPAI) |
| Agosto 2026 | Mayoría de obligaciones, incluyendo sistemas de alto riesgo |
| Agosto 2027 | Aplicación completa |

### Alcance para equipos de desarrollo con IA

licit se enfoca en las obligaciones de **deployers** (Art. 26-27) y en los requisitos de **transparencia** y **documentación técnica** que aplican a equipos que usan agentes IA para generar código.

**¿Tu equipo está en alcance?** Sí, si:
- Usas agentes IA (Claude Code, Cursor, Copilot, etc.) para generar código
- El software producido se despliega en la UE o afecta a ciudadanos de la UE
- Tu sistema de IA cae en alguna categoría del Annex III (alto riesgo)

### Artículos evaluados por licit

#### Art. 9 — Sistema de gestión de riesgos

> *"Los sistemas de IA de alto riesgo estarán sujetos a un sistema de gestión de riesgos [...] que consistirá en un proceso iterativo continuo."*

**Qué evalúa licit**: Presencia de guardrails, quality gates, budget limits, y herramientas de security scanning.

#### Art. 10 — Datos y gobernanza de datos

> *"Los conjuntos de datos de entrenamiento, validación y prueba estarán sujetos a prácticas adecuadas de gobernanza y gestión de datos."*

**Qué evalúa licit**: Perspectiva deployer — documenta que el proveedor del modelo gestiona los datos de entrenamiento.

#### Art. 12 — Record keeping

> *"Los sistemas de IA de alto riesgo se diseñarán y desarrollarán con capacidades que permitan el registro automático de eventos (logs)."*

**Qué evalúa licit**: Git history, audit trail (architect), provenance tracking, OpenTelemetry.

#### Art. 13 — Transparencia

> *"Los sistemas de IA de alto riesgo se diseñarán y desarrollarán de tal manera que su funcionamiento sea lo suficientemente transparente."*

**Qué evalúa licit**: Documentación Annex IV generada, changelog de configs de agentes, trazabilidad de requisitos.

#### Art. 14 — Supervisión humana

> *"Los sistemas de IA de alto riesgo se diseñarán y desarrollarán de tal manera que puedan ser supervisados eficazmente por personas físicas."*

**Qué evalúa licit**: Human review gates, dry-run, quality gates, rollback, budget limits.

#### Art. 26 — Obligaciones de los deployers

> *"Los deployers utilizarán los sistemas de IA de alto riesgo de conformidad con las instrucciones de uso."*

**Qué evalúa licit**: Presencia de configuraciones de agentes, monitoreo de operaciones.

#### Art. 27 — Evaluación de impacto en derechos fundamentales

> *"Antes de poner en servicio un sistema de IA de alto riesgo, los deployers llevarán a cabo una evaluación del impacto en los derechos fundamentales."*

**Qué genera licit**: FRIA completo con cuestionario interactivo de 5 pasos, 16 preguntas, auto-detección de 8 campos.

#### Annex IV — Documentación técnica

> *"La documentación técnica contendrá [...] una descripción general del sistema de IA, su finalidad prevista, proceso de desarrollo, pruebas y rendimiento."*

**Qué genera licit**: Documento con 6 secciones auto-pobladas desde metadatos del proyecto.

### Texto oficial

- [Reglamento (UE) 2024/1689 — EUR-Lex](https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32024R1689)
- [AI Act Explorer (Future of Life Institute)](https://artificialintelligenceact.eu/)

---

## OWASP Agentic Top 10 (2025)

### Contexto

El OWASP Top 10 for Agentic AI Security identifica los 10 principales riesgos de seguridad específicos para aplicaciones que usan agentes IA. Publicado por OWASP Foundation en 2025.

**No es regulación** — es un framework de buenas prácticas de seguridad ampliamente adoptado por la industria. Similar a como el OWASP Top 10 (web) es referencia estándar para seguridad web.

### Los 10 riesgos

| ID | Riesgo | Descripción | Relevancia para desarrollo |
|---|---|---|---|
| ASI01 | Excessive Agency | El agente tiene más permisos de los necesarios | Agentes que pueden escribir en cualquier archivo |
| ASI02 | Prompt Injection | Inputs maliciosos que manipulan el comportamiento | Código fuente con payloads en comentarios |
| ASI03 | Supply Chain | Dependencias vulnerables o comprometidas | Agentes que instalan paquetes sin verificar |
| ASI04 | Logging deficiente | Falta de registro de acciones del agente | Sin audit trail de qué hizo el agente |
| ASI05 | Output Handling | Output no validado usado en downstream | Código generado sin review que llega a prod |
| ASI06 | Sin Human Oversight | Falta de supervisión humana | Agentes que pushean directamente a main |
| ASI07 | Sandboxing insuficiente | Agente sin aislamiento adecuado | Acceso a todo el filesystem y red |
| ASI08 | Consumo de recursos | Sin límites de gasto/tokens | Agentes sin budget que gastan sin control |
| ASI09 | Error handling pobre | Errores que exponen estado o bypass controles | Agente que crashea dejando archivos corruptos |
| ASI10 | Exposición de datos | Filtración de datos sensibles | Agente que logea credenciales o PII |

### Texto oficial

- [OWASP Top 10 for Agentic AI](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

---

## Marcos futuros

### NIST AI RMF (AI 100-1) — Planificado V1

El AI Risk Management Framework del NIST define 4 funciones core:

1. **Govern**: Establecer políticas y procesos de gobernanza
2. **Map**: Contextualizar riesgos del sistema de IA
3. **Measure**: Evaluar y monitorear riesgos
4. **Manage**: Priorizar y tratar riesgos

Referencia: [NIST AI RMF (AI 100-1)](https://www.nist.gov/artificial-intelligence/ai-risk-management-framework)

### ISO/IEC 42001:2023 — Planificado V1

Estándar internacional que especifica requisitos para un sistema de gestión de IA (AIMS). Define:

- Cláusulas 4-10: Contexto, liderazgo, planificación, soporte, operación, evaluación, mejora
- Annex A: ~35 controles específicos de IA
- Annex B: Guía de implementación

Referencia: [ISO/IEC 42001:2023](https://www.iso.org/standard/81230.html)

---

## Limitaciones legales de licit

1. **licit no es asesoría legal.** Los reportes son evidencia técnica de soporte, no dictámenes legales.
2. **licit no clasifica riesgo.** La clasificación de un sistema como "alto riesgo" (Annex III) requiere análisis legal.
3. **licit no sustituye al DPO.** Si tu sistema procesa datos personales, necesitas un Data Protection Officer independientemente de licit.
4. **Los porcentajes de compliance son orientativos.** Un "80% compliant" no significa cumplimiento legal — un solo artículo incumplido puede tener consecuencias regulatorias.
5. **La auto-detección es heurística.** Las respuestas auto-detectadas en el FRIA son sugerencias basadas en señales técnicas, no determinaciones legales.
