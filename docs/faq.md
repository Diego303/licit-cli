# FAQ — Preguntas frecuentes

## Instalación y setup

### ¿Qué versión de Python necesito?

**Python 3.12 o superior**. licit usa `StrEnum` y otras features que requieren 3.12+.

```bash
python3.12 --version
# Si no lo tienes:
# Ubuntu/Debian: sudo apt install python3.12
# macOS: brew install python@3.12
# Windows: descargar de python.org
```

### Error: "pip install" se queda colgado

Si usas un sistema con múltiples versiones de Python, asegúrate de usar el pip correcto:

```bash
# Incorrecto (puede usar Python 3.10 u otra versión)
pip install licit-ai-cli

# Correcto
python3.12 -m pip install licit-ai-cli
```

### Error: `ModuleNotFoundError: No module named 'licit'`

La instalación no se completó correctamente. Reinstala:

```bash
python3.12 -m pip install -e ".[dev]"
```

Verifica que el entry point funciona:
```bash
python3.12 -m licit --version
```

---

## Configuración

### ¿Dónde va el archivo `.licit.yaml`?

En la raíz de tu proyecto, junto a `pyproject.toml` o `package.json`:

```
mi-proyecto/
├── .licit.yaml      ← aquí
├── pyproject.toml
├── src/
└── tests/
```

### ¿Puedo usar un nombre distinto para el archivo de config?

Sí, usa la opción `--config`:

```bash
licit --config mi-config.yaml status
```

### ¿Qué pasa si `.licit.yaml` tiene errores de sintaxis?

licit registra un warning y usa los valores por defecto. No falla con error.

```bash
$ licit --verbose status
# Warning: Failed to parse .licit.yaml: ...
# Using default configuration
```

### ¿Debo hacer commit de `.licit.yaml`?

**Sí**. Es la configuración compartida del equipo. Haz commit de `.licit.yaml`.

**No** hagas commit de `.licit/provenance.jsonl` ni `.licit/fria-data.json` (datos sensibles).

---

## Comandos

### `licit fria` / `licit report` no funcionan

Algunos comandos están **registrados** en el CLI pero su implementación completa es parte de fases futuras:

| Comando | Fase | Estado actual |
|---|---|---|
| `trace` | 2 | **Funcional** (v0.2.0) |
| `changelog` | 3 | **Funcional** (v0.3.0) |
| `fria` | 4 | **Funcional** (v0.4.0) |
| `annex-iv` | 4 | **Funcional** (v0.4.0) |
| `verify` | 4-5 | **Funcional** (v0.5.0 — EU AI Act + OWASP) |
| `report` | 6 | Skeleton |
| `gaps` | 6 | Skeleton |

Los comandos funcionales en v0.5.0 son: `init`, `status`, `connect`, `trace`, `changelog`, `fria`, `annex-iv`, `verify`.

### `licit init` no detecta mi lenguaje/framework

`ProjectDetector` busca archivos específicos:

| Lenguaje | Archivo buscado |
|---|---|
| Python | `pyproject.toml`, `requirements.txt` |
| JavaScript | `package.json` |
| TypeScript | `tsconfig.json` |
| Go | `go.mod` |
| Rust | `Cargo.toml` |
| Java | `pom.xml`, `build.gradle` |

| Framework | Cómo se detecta |
|---|---|
| FastAPI | `fastapi` en dependencias de `pyproject.toml` |
| Flask | `flask` en dependencias de `pyproject.toml` |
| Django | `django` en dependencias de `pyproject.toml` |
| React | `react` en dependencias de `package.json` |
| Next.js | `next` en dependencias de `package.json` |
| Express | `express` en dependencias de `package.json` |

Si tu lenguaje o framework no está soportado, abre un issue.

### `licit status` muestra "not collected" para provenance

Ejecuta `licit trace` para analizar el historial git y generar datos de proveniencia. Después de ejecutar trace, `licit status` mostrará las estadísticas de provenance.

```bash
licit trace --stats     # Analizar y mostrar estadísticas
licit status            # Ahora muestra datos de provenance
```

---

## Testing y desarrollo

### Los tests fallan con errores de structlog

Asegúrate de que `tests/conftest.py` configura structlog correctamente:

```python
import logging
import structlog

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL),
    cache_logger_on_first_use=False,
)
```

El error más común es `ValueError: I/O operation on closed file` cuando Click's `CliRunner` cierra stderr y structlog intenta escribir en él. La solución está en usar `WriteLoggerFactory()` (no `PrintLoggerFactory(file=sys.stderr)`).

### mypy muestra errores en imports de módulos futuros

Los imports de módulos de fases futuras (como `licit.reports.unified`) usan `# type: ignore[import-not-found]`:

```python
from licit.reports.unified import (  # type: ignore[import-not-found]
    UnifiedReportGenerator,
)
```

El comentario `type: ignore` debe ir en la línea del `from`, no en las líneas de los nombres importados. Si ruff reformatea el import a multilínea, verifica que el comentario quede en la línea correcta.

> **Nota**: Los módulos de Fases 2-5 (provenance, changelog, eu_ai_act, owasp_agentic) ya están implementados y se importan directamente sin `type: ignore`. Solo `reports/` (Phase 6) usa stubs lazy.

### ruff reporta UP042 en mis enums

Usa `StrEnum` en lugar de `(str, Enum)`:

```python
# ruff UP042 error:
class MiEnum(str, Enum):  # ← error
    VALUE = "value"

# Correcto:
from enum import StrEnum
class MiEnum(StrEnum):    # ← correcto
    VALUE = "value"
```

### ¿Cómo ejecuto un solo test?

```bash
# Por nombre
python3.12 -m pytest tests/test_cli.py::TestCLIHelp::test_help -q

# Por patrón (keyword)
python3.12 -m pytest tests/ -q -k "test_init"

# Por archivo
python3.12 -m pytest tests/test_core/test_project.py -q
```

---

## Compliance

### ¿licit reemplaza a un abogado/consultor de compliance?

**No.** licit es una herramienta de asistencia que automatiza la recopilación de evidencia y genera reportes. Las decisiones finales de compliance deben ser revisadas por profesionales cualificados.

### ¿El reporte de licit es suficiente para una auditoría EU AI Act?

El reporte de licit es un **punto de partida**. Proporciona evidencia técnica estructurada que puede complementar la documentación de compliance. Para una auditoría formal, necesitarás:

1. Revisión legal del FRIA
2. Documentación organizacional adicional
3. Evidencia de procesos de gestión de riesgos
4. Registros de formación del equipo

### ¿Qué pasa si mi proyecto no es "alto riesgo" según EU AI Act?

Si tu sistema de IA no cae en la categoría de alto riesgo, muchos requisitos del EU AI Act no aplican. licit permite marcar requisitos como `n/a` (no aplica). Sin embargo, es buena práctica cumplir con los requisitos de transparencia (Art. 13) y supervisión humana (Art. 14) independientemente de la clasificación de riesgo.

### ¿OWASP Agentic Top 10 es obligatorio?

No es regulación, es un framework de buenas prácticas de seguridad. Sin embargo, seguir las recomendaciones del OWASP Agentic Top 10 reduce significativamente los riesgos de seguridad cuando se usan agentes IA en desarrollo.

---

## Seguridad

### ¿licit envía datos a algún servidor?

**No.** licit opera 100% localmente. No hay telemetría, analytics ni comunicación con servidores externos.

### ¿Puedo usar licit en un entorno air-gapped?

Sí. licit no requiere conexión a internet para funcionar. Solo necesitas instalar las dependencias previamente.

### ¿Es seguro hacer commit de los reportes generados?

Los reportes en `.licit/reports/` generalmente son seguros para commit. Contienen evaluaciones de compliance, no datos sensibles. Sin embargo, revisa el contenido antes de subir a un repo público.

Los archivos que **no** debes commitear:
- `.licit/provenance.jsonl` — Contiene información de contribuidores
- `.licit/fria-data.json` — Puede contener datos sensibles del FRIA
- Claves de firmado (`.licit/signing-key`)

---

## Problemas conocidos (v0.5.0)

| Problema | Estado | Workaround |
|---|---|---|
| Comandos `report` y `gaps` muestran error | Esperado | Dependen de Phase 6 (reports). Usar `verify` para compliance check |
| No detecta frameworks Go/Rust/Java | Limitacion | Detecta el lenguaje pero no frameworks especificos |
| Heuristicas de provenance pueden dar falsos positivos | Limitacion | Ajustar `confidence_threshold` en config |
| Session reader solo soporta Claude Code | Limitacion | Mas readers en fases futuras |
| Pipe `\|` en nombre de organizacion rompe tabla Markdown en Annex IV | Limitacion | Evitar pipe en nombres de organizacion |
| Solo formato Markdown para reportes de compliance | Esperado | JSON/HTML en Fase 6 |
| Markdown differ solo soporta headings ATX (`#`) | Limitacion | Los headings setext (`===`/`---`) no se detectan |
| FRIA `run_interactive()` requiere terminal | Limitacion | No se puede ejecutar en modo batch; usar `--update` con datos pre-generados |

---

## Glosario

| Término | Definición |
|---|---|
| **Provenance** | Origen y autoría del código (humano vs IA) |
| **FRIA** | Fundamental Rights Impact Assessment (Art. 27 EU AI Act) |
| **Annex IV** | Documentación técnica requerida por el EU AI Act |
| **SARIF** | Static Analysis Results Interchange Format — formato estándar para hallazgos de seguridad |
| **SBOM** | Software Bill of Materials — inventario de componentes |
| **Guardrail** | Control que limita el comportamiento de un agente IA |
| **Human review gate** | Punto de control que requiere aprobación humana |
| **Attestation** | Verificación criptográfica de integridad de datos |
| **Compliance rate** | Porcentaje de requisitos cumplidos vs total evaluable |
| **Gap** | Brecha entre el estado actual y un requisito de compliance |
