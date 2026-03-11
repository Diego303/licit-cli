# Guía de desarrollo

Guía para contribuidores y desarrolladores que quieran trabajar en licit.

---

## Requisitos previos

- **Python 3.12+** (obligatorio; el proyecto usa `StrEnum` y otras features de 3.12)
- **Git** (para tests de detección de proyecto)
- **pip** (viene con Python)

Verifica tu versión:
```bash
python3.12 --version
# Python 3.12.x
```

---

## Setup del entorno

```bash
# Clonar el repositorio
git clone https://github.com/Diego303/licit-cli.git
cd licit-cli

# Instalar en modo desarrollo con dependencias de dev
python3.12 -m pip install -e ".[dev]"

# Verificar la instalación
licit --version
# licit, version 0.2.0
```

### Dependencias de desarrollo

| Paquete | Versión | Propósito |
|---|---|---|
| pytest | 8.0+ | Framework de testing |
| pytest-cov | 5.0+ | Cobertura de código |
| ruff | 0.4+ | Linter y formatter |
| mypy | 1.9+ | Type checking estricto |

---

## Comandos de desarrollo

```bash
# Tests
python3.12 -m pytest tests/ -q              # Ejecutar todos los tests
python3.12 -m pytest tests/ -q -x           # Parar en el primer fallo
python3.12 -m pytest tests/test_cli.py -q   # Solo tests de CLI
python3.12 -m pytest tests/ -q --tb=short   # Tracebacks cortos
python3.12 -m pytest tests/ --cov=licit     # Con cobertura

# Linting
python3.12 -m ruff check src/licit/        # Verificar errores
python3.12 -m ruff check src/licit/ --fix  # Auto-corregir

# Type checking
python3.12 -m mypy src/licit/ --strict     # Verificar tipos (modo estricto)

# CLI
python3.12 -m licit --help                  # Ayuda general
python3.12 -m licit init                    # Probar init
python3.12 -m licit status                  # Probar status
```

---

## Estructura del código

```
src/licit/
├── __init__.py         # __version__ = "0.2.0"
├── __main__.py         # Entry point: python -m licit
├── py.typed            # PEP 561 marker
├── cli.py              # Todos los comandos Click
├── config/
│   ├── schema.py       # Modelos Pydantic v2 (LicitConfig, etc.)
│   ├── loader.py       # load_config(), save_config()
│   └── defaults.py     # DEFAULTS, CONFIG_FILENAME, DATA_DIR
├── core/
│   ├── models.py       # Enums + dataclasses de dominio
│   ├── project.py      # ProjectDetector
│   └── evidence.py     # EvidenceCollector + EvidenceBundle
├── logging/
│   └── setup.py        # setup_logging(verbose)
├── provenance/         # Fase 2 (COMPLETADA)
│   ├── heuristics.py   # 6 heurísticas de detección AI
│   ├── git_analyzer.py # Análisis de git history
│   ├── store.py        # Store JSONL append-only
│   ├── attestation.py  # HMAC-SHA256 + Merkle tree
│   ├── tracker.py      # Orquestador de provenance
│   ├── report.py       # Generador de reportes Markdown
│   └── session_readers/
│       ├── base.py     # Protocol SessionReader
│       └── claude_code.py  # Reader Claude Code
├── changelog/          # Fase 3
├── frameworks/         # Fases 4-5
├── connectors/         # Fase 7
└── reports/            # Fase 6
```

---

## Convenciones de código

### 1. Pydantic solo para configuración

```python
# Correcto — config usa Pydantic
class ProvenanceConfig(BaseModel):
    enabled: bool = True

# Correcto — dominio usa dataclasses
@dataclass
class ProvenanceRecord:
    file_path: str
    source: str
```

### 2. StrEnum para enums

```python
# Correcto — Python 3.12+
class ComplianceStatus(StrEnum):
    COMPLIANT = "compliant"

# Incorrecto — ruff UP042
class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
```

### 3. Protocoles para interfaces

```python
# Correcto — typing.Protocol
class Evaluator(Protocol):
    def evaluate(self, evidence: EvidenceBundle) -> list[ControlResult]: ...

# Incorrecto — ABC
class Evaluator(ABC):
    @abstractmethod
    def evaluate(self, evidence: EvidenceBundle) -> list[ControlResult]: ...
```

### 4. structlog para logging

```python
import structlog
logger = structlog.get_logger()

# Correcto — eventos + datos estructurados
logger.info("config_loaded", path=str(config_path), framework="eu-ai-act")

# Incorrecto — mensajes de texto libre
logger.info(f"Config loaded from {config_path} for framework eu-ai-act")
```

### 5. Lazy imports para módulos futuros

Cuando un comando necesita un módulo que aún no existe, usa lazy imports con `type: ignore`:

```python
@main.command()
def changelog() -> None:
    """Generate agent config changelog."""
    try:
        from licit.changelog.renderer import (  # type: ignore[import-not-found]
            ChangelogRenderer,
        )
    except ImportError:
        click.echo("Changelog not yet implemented.")
        raise SystemExit(1)
```

> **Nota**: Los módulos de Fase 2 (provenance) ya están implementados y se importan directamente sin `type: ignore`.

### 6. Ruff y mypy

- **ruff** con reglas: `E` (errores), `F` (f-strings), `I` (imports), `UP` (upgrades)
- **mypy** en modo `--strict`
- Línea máxima: 100 caracteres
- Target: Python 3.12

---

## Testing

### Estructura de tests

```
tests/
├── conftest.py                     # Fixtures compartidos
├── test_cli.py                     # 13 tests
├── test_qa_edge_cases.py           # 61 tests (QA Phase 1)
├── test_config/
│   ├── test_schema.py              # 7 tests
│   └── test_loader.py              # 9 tests
├── test_core/
│   ├── test_project.py             # 12 tests
│   └── test_evidence.py            # 11 tests
└── test_provenance/
    ├── test_heuristics.py          # 23 tests
    ├── test_git_analyzer.py        # 15 tests
    ├── test_store.py               # 15 tests
    ├── test_attestation.py         # 13 tests
    ├── test_tracker.py             # 7 tests
    ├── test_session_reader.py      # 13 tests
    ├── test_qa_edge_cases.py       # 81 tests (QA Phase 2)
    └── fixtures/                   # Datos de test
```

**Total: 280 tests**

### Fixtures disponibles (conftest.py)

```python
# Proyecto temporal con pyproject.toml
def tmp_project(tmp_path) -> Path: ...

# Proyecto temporal con git inicializado
def git_project(tmp_path) -> Path: ...

# Factory de ProjectContext
def make_context(root_dir, name, languages, ...) -> ProjectContext: ...

# Factory de EvidenceBundle
def make_evidence(has_provenance, has_fria, ...) -> EvidenceBundle: ...
```

### Supresión de logs en tests

Los tests configuran structlog a nivel CRITICAL para evitar ruido:

```python
# tests/conftest.py
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL),
    cache_logger_on_first_use=False,
)
```

### Escribir un nuevo test

```python
# tests/test_core/test_mi_modulo.py

def test_mi_feature(tmp_project: Path) -> None:
    """Descripción clara de qué se testea."""
    # Arrange
    (tmp_project / "CLAUDE.md").write_text("# Agent config")

    # Act
    resultado = mi_funcion(str(tmp_project))

    # Assert
    assert resultado.valor_esperado == "algo"
```

### Tests con Click CLI

```python
from click.testing import CliRunner
from licit.cli import main

def test_mi_comando(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["mi-comando", "--flag"])
        assert result.exit_code == 0
        assert "texto esperado" in result.output
```

---

## Añadir un nuevo comando CLI

1. Define el comando en `src/licit/cli.py`:

```python
@main.command()
@click.pass_context
def mi_comando(ctx: click.Context) -> None:
    """Descripción del comando."""
    config = ctx.obj["config"]
    # ... implementación ...
    click.echo("Done.")
```

2. Añade tests en `tests/test_cli.py`:

```python
def test_mi_comando(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["mi-comando"])
        assert result.exit_code == 0
```

3. Verifica:

```bash
python3.12 -m pytest tests/test_cli.py -q
python3.12 -m ruff check src/licit/cli.py
python3.12 -m mypy src/licit/cli.py --strict
```

---

## Añadir un nuevo modelo de configuración

1. Define el modelo en `src/licit/config/schema.py`:

```python
class MiConfig(BaseModel):
    enabled: bool = True
    mi_campo: str = "default"
```

2. Añádelo a `LicitConfig`:

```python
class LicitConfig(BaseModel):
    # ... campos existentes ...
    mi_config: MiConfig = Field(default_factory=MiConfig)
```

3. Añade tests en `tests/test_config/test_schema.py`.

---

## Flujo de trabajo recomendado

```
1. Crear branch feature
   git checkout -b feat/mi-feature

2. Implementar
   - Código en src/licit/
   - Tests en tests/

3. Verificar
   python3.12 -m pytest tests/ -q      # 280+ tests passing
   python3.12 -m ruff check src/licit/  # All checks passed
   python3.12 -m mypy src/licit/ --strict  # No issues found

4. Commit y PR
   git add src/licit/ tests/
   git commit -m "feat: mi nueva feature"
```

---

## Fases de implementación

| Fase | Módulos | Directorio | Estado |
|---|---|---|---|
| 1 | `cli.py`, `config/`, `core/`, `logging/` | múltiples | **COMPLETADA** |
| 2 | `heuristics.py`, `git_analyzer.py`, `store.py`, `attestation.py`, `tracker.py`, `report.py`, `session_readers/` | `provenance/` | **COMPLETADA** |
| 3 | `watcher.py`, `differ.py`, `classifier.py`, `renderer.py` | `changelog/` | Pendiente |
| 4 | `requirements.py`, `evaluator.py`, `fria.py`, `annex_iv.py`, `templates/` | `frameworks/eu_ai_act/` | Pendiente |
| 5 | `requirements.py`, `evaluator.py`, `templates/` | `frameworks/owasp_agentic/` | Pendiente |
| 6 | `unified.py`, `gap_analyzer.py`, `markdown.py`, `json_fmt.py`, `html.py` | `reports/` | Pendiente |
| 7 | `base.py`, `architect.py`, `vigil.py` | `connectors/` | Pendiente |

Cada fase tiene su sección detallada en el [plan de implementación](../Licit_V0_Plan_Implementacion.md).
