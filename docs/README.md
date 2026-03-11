# Documentación de licit

> Herramienta CLI de compliance regulatorio y trazabilidad de código para equipos de desarrollo con IA.

## Índice

| Documento | Descripción |
|---|---|
| [Inicio rápido](inicio-rapido.md) | Guía para tener licit funcionando en 5 minutos |
| [Arquitectura](arquitectura.md) | Arquitectura del sistema, módulos, fases y decisiones de diseño |
| [Guía de CLI](guia-cli.md) | Referencia completa de todos los comandos y opciones |
| [Configuración](configuracion.md) | Guía de configuración de `.licit.yaml` con todos los campos |
| [Modelos de datos](modelos.md) | Enums, dataclasses y schemas Pydantic usados internamente |
| [Seguridad](seguridad.md) | Modelo de amenazas, firmado criptográfico, protección de datos |
| [Compliance](compliance.md) | Marcos regulatorios soportados: EU AI Act y OWASP Agentic Top 10 |
| [Buenas prácticas](buenas-practicas.md) | Recomendaciones para integrar licit en tu flujo de trabajo |
| [Desarrollo](desarrollo.md) | Guía para contribuidores: setup, testing, linting, convenciones |
| [Provenance](provenance.md) | Sistema de trazabilidad: heurísticas, git analyzer, store, attestation, session readers |
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

- **v0.2.0** — Fase 1 (Foundation) + Fase 2 (Provenance) completadas
- Python 3.12+ requerido
- 10 comandos CLI registrados, 4 funcionales (`init`, `status`, `connect`, `trace`)
- 280 tests, mypy strict, ruff clean

## Licencia

MIT — ver [LICENSE](../LICENSE) en la raíz del proyecto.
