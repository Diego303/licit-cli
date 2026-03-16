# Glosario

Términos técnicos, regulatorios y de dominio usados en licit y su documentación.

---

## Términos regulatorios

| Término | Definición | Contexto en licit |
|---|---|---|
| **EU AI Act** | Reglamento (UE) 2024/1689. Primera regulación integral de IA a nivel mundial. En vigor desde agosto 2024, aplicación gradual hasta 2027. | Marco regulatorio evaluado por `licit verify --framework eu-ai-act` |
| **FRIA** | Fundamental Rights Impact Assessment. Evaluación de impacto en derechos fundamentales requerida por Art. 27 del EU AI Act para sistemas de alto riesgo. | Generado con `licit fria` |
| **Annex IV** | Anexo IV del EU AI Act. Define la documentación técnica requerida para sistemas de IA: propósito, diseño, desarrollo, testing, rendimiento. | Generado con `licit annex-iv` |
| **Deployer** | Persona u organización que despliega un sistema de IA para su uso. Distinto del proveedor (provider) que lo desarrolla. | licit evalúa obligaciones de deployer (Art. 26) |
| **Sistema de alto riesgo** | Sistema de IA clasificado como de alto riesgo según Annex III del EU AI Act. Sujeto a requisitos adicionales de compliance. | El FRIA es obligatorio para estos sistemas |
| **OWASP Agentic Top 10** | Lista de los 10 principales riesgos de seguridad para aplicaciones que usan agentes IA (2025). Publicado por OWASP Foundation. | Marco evaluado por `licit verify --framework owasp` |
| **NIST AI RMF** | AI Risk Management Framework (AI 100-1). Marco de gestión de riesgos de IA del NIST. | Planificado para V1 |
| **ISO/IEC 42001** | Estándar internacional para sistemas de gestión de IA. Define requisitos para establecer, implementar y mejorar sistemas de gestión de IA. | Planificado para V1 |
| **Compliance rate** | Porcentaje de requisitos evaluables que están cumplidos. Fórmula: `compliant / (total - n/a - not_evaluated) * 100` | Mostrado en reportes y `licit status` |

---

## Términos técnicos

| Término | Definición | Contexto en licit |
|---|---|---|
| **Provenance** | Origen y autoría del código. Tracking de qué código fue escrito por humanos, generado por IA, o una combinación. | `licit trace` analiza provenance |
| **Heurística** | Regla basada en señales observables (no certezas) para inferir una clasificación. licit usa 6 heurísticas ponderadas para clasificar commits como AI/human/mixed. | Motor de heurísticas en `provenance/heuristics.py` |
| **Attestation** | Verificación criptográfica de integridad. En licit: HMAC-SHA256 para registros individuales, Merkle tree para batches. | `provenance.sign: true` en config |
| **Merkle tree** | Estructura de datos en forma de árbol binario donde cada nodo es el hash de sus hijos. Permite verificar integridad de conjuntos de datos. | Usado para firmar batches de provenance |
| **HMAC-SHA256** | Hash-based Message Authentication Code con SHA-256. Firma criptográfica que prueba que los datos no han sido alterados. | Firmado de registros individuales de provenance |
| **SARIF** | Static Analysis Results Interchange Format. Formato estándar OASIS para resultados de análisis estático de código. Versión 2.1.0. | Leído por VigilConnector |
| **SBOM** | Software Bill of Materials. Inventario formal de componentes de software. Formato CycloneDX usado por vigil. | Leído por VigilConnector (`sbom_path`) |
| **CycloneDX** | Estándar OWASP para SBOM. Formato JSON/XML para describir componentes de software, sus versiones y vulnerabilidades. | Formato de SBOM soportado |
| **JSONL** | JSON Lines. Formato donde cada línea es un JSON object independiente. | Store de provenance (`.licit/provenance.jsonl`) |
| **Merge + Dedup** | Store que fusiona registros nuevos con existentes, manteniendo solo el más reciente por archivo. Evita crecimiento ilimitado. | ProvenanceStore |

---

## Términos de agentes IA

| Término | Definición | Contexto en licit |
|---|---|---|
| **Agente IA** | Sistema de IA que opera de forma semi-autónoma o autónoma para realizar tareas. En desarrollo de software: Claude Code, Cursor, Copilot, Codex, architect. | licit rastrea código generado por agentes |
| **Guardrail** | Control que limita el comportamiento de un agente IA. Ejemplos: archivos protegidos, comandos bloqueados, reglas de código. | Extraído de architect config, cuenta para compliance |
| **Quality gate** | Verificación automatizada que debe pasar antes de aceptar el output de un agente. Ejemplos: lint, typecheck, test. | Extraído de architect config |
| **Human review gate** | Punto de control que requiere aprobación humana. Ejemplo: branch protection con required reviews en GitHub. | Detectado de CI/CD config |
| **Dry-run** | Modo de ejecución que simula acciones sin aplicar cambios. Permite previsualizar el comportamiento del agente. | Detectado de architect config |
| **Rollback** | Capacidad de revertir cambios realizados por un agente. Típicamente via git revert o mecanismos similares. | Detectado de architect config |
| **Session log** | Registro de una sesión de trabajo de un agente IA. Contiene herramientas usadas, archivos modificados, timestamps. | Claude Code session reader |
| **Budget limit** | Límite de gasto en tokens/API calls para controlar el consumo de recursos de un agente. | Extraído de `costs.budget_usd` |

---

## Términos de la herramienta

| Término | Definición |
|---|---|
| **licit** | Herramienta CLI de compliance regulatorio para equipos que usan IA en desarrollo de software |
| **EvidenceBundle** | Dataclass con 18 campos que agrupa toda la evidencia recopilada del proyecto |
| **ProjectContext** | Dataclass que describe el contexto auto-detectado del proyecto (lenguajes, frameworks, CI/CD, etc.) |
| **ControlRequirement** | Un requisito individual de un marco regulatorio (ej: Art. 9(1) del EU AI Act) |
| **ControlResult** | Resultado de evaluar un requisito contra el proyecto (status, evidencia, recomendaciones) |
| **GapItem** | Brecha de compliance identificada con recomendación accionable, esfuerzo estimado, y herramientas sugeridas |
| **Connector** | Integración read-only con herramientas externas (architect, vigil) que enriquece la evidencia |
| **ConnectorResult** | Resultado de la ejecución de un connector (archivos leídos, errores) |
| **ComplianceFramework** | Protocol que define la interfaz para evaluadores de marcos regulatorios |
| **ConfigChange** | Cambio detectado en un archivo de configuración de agente IA, con severidad MAJOR/MINOR/PATCH |
