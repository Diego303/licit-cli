# Documentación de licit

> Herramienta CLI de compliance regulatorio y trazabilidad de código para equipos de desarrollo con IA.

## Índice

| Documento | Descripción |
|---|---|
| [Inicio rápido](inicio-rapido.md) | Guía para tener licit funcionando en 5 minutos |
| [Guía de CLI](guia-cli.md) | Referencia completa de todos los comandos y opciones |
| [Interpretación de reportes](interpretacion-reportes.md) | Cómo leer y actuar sobre los reportes de compliance y gap analysis |
| [Guía FRIA](guia-fria.md) | Orientación pregunta por pregunta para completar el FRIA (Art. 27) |
| [Guía para auditores](guia-auditor.md) | Verificación de compliance, evidencia, preparación para auditoría regulatoria |
| [Integración CI/CD](ci-cd.md) | GitHub Actions, GitLab CI, Jenkins — licit como gate de compliance |
| [Configuración](configuracion.md) | Guía de configuración de `.licit.yaml` con todos los campos |
| [Compliance](compliance.md) | Marcos regulatorios soportados: EU AI Act y OWASP Agentic Top 10 |
| [Arquitectura](arquitectura.md) | Arquitectura del sistema, módulos, fases y decisiones de diseño |
| [Modelos de datos](modelos.md) | Enums, dataclasses y schemas Pydantic usados internamente |
| [Provenance](provenance.md) | Sistema de trazabilidad: heurísticas, git analyzer, store, attestation |
| [Changelog](changelog.md) | Sistema de changelog: watcher, differ, classifier, renderer |
| [Seguridad](seguridad.md) | Modelo de amenazas, firmado criptográfico, protección de datos |
| [Buenas prácticas](buenas-practicas.md) | Recomendaciones para integrar licit en tu flujo de trabajo |
| [Desarrollo](desarrollo.md) | Guía para contribuidores: setup, testing, linting, convenciones |
| [FAQ](faq.md) | Preguntas frecuentes y resolución de problemas |

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

- **v0.6.0** — Fases 1-6 completadas (Foundation + Provenance + Changelog + EU AI Act + OWASP Agentic Top 10 + Reports)
- Python 3.12+ requerido
- 10 comandos CLI, todos funcionales
- 706 tests, mypy strict, ruff clean

## Licencia

MIT — ver [LICENSE](../LICENSE) en la raíz del proyecto.
