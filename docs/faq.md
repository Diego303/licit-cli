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

### `licit trace` / `licit changelog` / `licit fria` no funcionan

Estos comandos están **registrados** en el CLI pero su implementación completa es parte de fases futuras:

| Comando | Fase | Estado actual |
|---|---|---|
| `trace` | 2 | Skeleton (muestra error informativo) |
| `changelog` | 3 | Skeleton |
| `fria` | 4 | Skeleton |
| `annex-iv` | 4 | Skeleton |
| `report` | 6 | Skeleton |
| `gaps` | 6 | Skeleton |
| `verify` | 6 | Skeleton |

Los comandos funcionales en v0.1.0 son: `init`, `status`, `connect`.

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

Es normal en v0.1.0. La recopilación de provenance se implementa en Fase 2. Ejecuta `licit trace` una vez disponible.

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

Los imports de módulos de fases futuras (como `licit.provenance.store`) usan `# type: ignore[import-not-found]`:

```python
from licit.provenance.store import (  # type: ignore[import-not-found]
    ProvenanceStore,
)
```

El comentario `type: ignore` debe ir en la línea del `from`, no en las líneas de los nombres importados. Si ruff reformatea el import a multilínea, verifica que el comentario quede en la línea correcta.

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

## Problemas conocidos (v0.1.0)

| Problema | Estado | Workaround |
|---|---|---|
| Comandos de fases 2-7 muestran error | Esperado | Usar `init`, `status`, `connect` |
| No detecta frameworks Go/Rust/Java | Limitación | Detecta el lenguaje pero no frameworks específicos |
| Provenance no recopilada | Esperado | Implementación en Fase 2 |
| FRIA no interactivo | Esperado | Implementación en Fase 4 |
| Solo formato Markdown para reportes | Esperado | JSON/HTML en Fase 6 |

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
