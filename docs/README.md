# Documentación de licit

> Herramienta CLI de compliance regulatorio y trazabilidad de código para equipos de desarrollo con IA.

## Índice

### Para usuarios

| Documento | Descripción |
|---|---|
| [Inicio rápido](inicio-rapido.md) | Guía para tener licit funcionando en 5 minutos |
| [Guía de CLI](guia-cli.md) | Referencia completa de todos los comandos y opciones |
| [Configuración](configuracion.md) | Guía de configuración de `.licit.yaml` con todos los campos |
| [Conectores](conectores.md) | Architect y vigil: qué leen, cómo configurarlos, cómo alimentan compliance |
| [Ejemplos y recetas](ejemplos.md) | Flujos de trabajo completos para casos de uso comunes |
| [Buenas prácticas](buenas-practicas.md) | Recomendaciones para integrar licit en tu flujo de trabajo |
| [FAQ](faq.md) | Preguntas frecuentes y resolución de problemas |

### Para compliance y auditoría

| Documento | Descripción |
|---|---|
| [Compliance](compliance.md) | Marcos regulatorios soportados: EU AI Act y OWASP Agentic Top 10 |
| [Marco legal](marco-legal.md) | Contexto legal del EU AI Act, OWASP, NIST, ISO — con referencias oficiales |
| [Interpretación de reportes](interpretacion-reportes.md) | Cómo leer y actuar sobre los reportes de compliance y gap analysis |
| [Guía FRIA](guia-fria.md) | Orientación pregunta por pregunta para completar el FRIA (Art. 27) |
| [Guía para auditores](guia-auditor.md) | Verificación de compliance, evidencia, preparación para auditoría regulatoria |
| [Integración CI/CD](ci-cd.md) | GitHub Actions, GitLab CI, Jenkins — licit como gate de compliance |
| [Guía enterprise](enterprise.md) | Adopción organizacional, modelo de madurez, integración con GRC |

### Para desarrolladores

| Documento | Descripción |
|---|---|
| [Arquitectura](arquitectura.md) | Arquitectura del sistema, módulos, fases y decisiones de diseño |
| [Modelos de datos](modelos.md) | Enums, dataclasses y schemas Pydantic usados internamente |
| [Provenance](provenance.md) | Sistema de trazabilidad: heurísticas, git analyzer, store, attestation |
| [Changelog](changelog.md) | Sistema de changelog: watcher, differ, classifier, renderer |
| [API programática](api-programatica.md) | Uso de licit desde Python: imports, clases, ejemplos |
| [Seguridad](seguridad.md) | Modelo de amenazas, firmado criptográfico, protección de datos |
| [Desarrollo](desarrollo.md) | Guía para contribuidores: setup, testing, linting, convenciones |
| [Migración V0 → V1](migracion-v1.md) | Contrato de estabilidad, cambios planificados, pasos de migración |

### Referencia

| Documento | Descripción |
|---|---|
| [Glosario](glosario.md) | Términos regulatorios, técnicos y de dominio |

## Inicio rápido

```bash
# Instalar
pip install licit-ai-cli

# Inicializar en tu proyecto
cd tu-proyecto/
licit init

# Ver estado
licit status

# Rastrear proveniencia del código
licit trace --stats

# Generar reporte de compliance
licit report
```

## Versión actual

- **v0.7.0** — Fases 1-7 completadas (Foundation + Provenance + Changelog + EU AI Act + OWASP Agentic Top 10 + Reports + Connectors)
- Python 3.12+ requerido
- 10 comandos CLI, todos funcionales
- 789 tests, mypy strict, ruff clean
- Connectors: architect (reports, audit log, config) + vigil (SARIF, SBOM)

## Licencia

MIT — ver [LICENSE](../LICENSE) en la raíz del proyecto.
