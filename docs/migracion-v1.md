# Guía de migración V0 → V1

> **Estado**: Este documento se actualizará cuando V1 entre en desarrollo. Por ahora documenta el contrato de V0 y los cambios planificados.

---

## Contrato de estabilidad V0

### Lo que NO cambiará en V1

Estos elementos son estables y no habrá breaking changes:

1. **CLI commands**: Los 10 comandos (`init`, `trace`, `changelog`, `fria`, `annex-iv`, `report`, `gaps`, `verify`, `status`, `connect`) mantienen su interfaz.
2. **Exit codes**: `verify` seguirá retornando 0/1/2.
3. **Config schema**: `.licit.yaml` seguirá siendo compatible — campos nuevos serán opcionales con defaults.
4. **Data formats**: `provenance.jsonl`, `fria-data.json`, reportes MD/JSON/HTML mantienen su estructura.
5. **EvidenceBundle**: Los 18 campos existentes no cambiarán. Se pueden añadir campos nuevos.

### Lo que PUEDE cambiar en V1

1. **Nuevos campos en config** — `frameworks.nist_ai_rmf`, `frameworks.iso_42001` pasarán a `true` por default cuando se implementen.
2. **Nuevos campos en EvidenceBundle** — Para soportar SBOM, NIST, ISO.
3. **Nuevos requirements** — Más `ControlRequirement` en EU AI Act y OWASP.
4. **Plugin system** — Mecanismo para registrar frameworks y connectors custom.
5. **Sigstore integration** — `provenance.sign` podría soportar keyless signing además de HMAC.

---

## Nuevos frameworks en V1

### NIST AI RMF (AI 100-1)

El NIST AI Risk Management Framework se estructurará como un evaluador que implementa el Protocol `ComplianceFramework`:

- **Funciones**: Govern, Map, Measure, Manage
- **Categorías**: ~20 subcategorías evaluables
- **Evidencia**: Reutilizará `EvidenceBundle` existente + campos nuevos para data governance avanzada

### ISO/IEC 42001

El estándar de gestión de IA se estructurará como evaluador con:

- **Cláusulas**: 4-10 (Context, Leadership, Planning, Support, Operation, Evaluation, Improvement)
- **Controles Annex A**: ~35 controles evaluables
- **Evidencia**: Requerirá campos nuevos para política organizacional y training records

---

## Plugin system (V1)

V1 introducirá un mecanismo de registro de plugins:

```python
# licit-mi-framework/src/mi_framework/__init__.py
from licit.frameworks.base import ComplianceFramework

class MiFrameworkEvaluator:
    name = "mi-framework"
    version = "1.0"
    description = "Mi marco custom"

    def get_requirements(self) -> list[ControlRequirement]: ...
    def evaluate(self, context, evidence) -> list[ControlResult]: ...
```

Registro via entry points en `pyproject.toml`:

```toml
[project.entry-points."licit.frameworks"]
mi-framework = "mi_framework:MiFrameworkEvaluator"
```

---

## Pasos de migración (cuando V1 esté disponible)

### 1. Actualizar

```bash
pip install --upgrade licit-ai-cli
licit --version
# licit, version 1.0.0
```

### 2. Verificar config

```bash
# V1 añadirá nuevos defaults. Verificar que tu config es válida:
licit status
```

### 3. Re-evaluar

```bash
# Los nuevos frameworks pueden detectar nuevas brechas:
licit report --format json -o v1-baseline.json
licit gaps
```

### 4. Comparar con V0

```bash
# Compara el reporte V0 con V1 para ver cambios:
diff v0-report.json v1-baseline.json
```

---

## Timeline estimado

| Hito | Estimación |
|---|---|
| V0.x (session readers, PDF, GitHub Action) | 2-3 semanas post-V0 |
| V1.0-alpha (NIST AI RMF) | 4 semanas post-V0 |
| V1.0-beta (ISO 42001, plugin system) | 6 semanas post-V0 |
| V1.0 release | 8 semanas post-V0 |

---

## Preguntas frecuentes de migración

### ¿Necesito re-ejecutar `licit init`?

No. Tu `.licit.yaml` existente seguirá funcionando. Los nuevos campos tomarán valores default.

### ¿Se pierden los datos de provenance?

No. `provenance.jsonl` es forwards-compatible. V1 puede añadir campos a nuevos registros sin invalidar los existentes.

### ¿El FRIA existente sigue siendo válido?

Sí. Si V1 añade nuevas preguntas al FRIA, puedes actualizarlo con `licit fria --update`.

### ¿Los reportes de V0 se pueden comparar con los de V1?

Sí, si usas formato JSON. La estructura base (`overall`, `frameworks[]`, `results[]`) no cambiará. V1 puede añadir campos nuevos pero no eliminar los existentes.
