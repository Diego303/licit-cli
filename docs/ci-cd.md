# Integración CI/CD

## Visión general

licit funciona como gate de compliance en pipelines CI/CD. El comando `licit verify` retorna exit codes que determinan si un pipeline pasa o falla:

| Exit code | Significado | Acción del pipeline |
|---|---|---|
| `0` | **COMPLIANT** — Todos los requisitos cumplidos | Pipeline continúa |
| `1` | **NON_COMPLIANT** — Algún requisito crítico no cumplido | Pipeline falla |
| `2` | **PARTIAL** — Requisitos parcialmente cumplidos | Configurable (falla o warning) |

---

## GitHub Actions

### Gate básico

```yaml
# .github/workflows/compliance.yml
name: Compliance Check

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # licit necesita historial git completo

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install licit
        run: pip install licit-ai-cli

      - name: Verify compliance
        run: licit verify
```

> **`fetch-depth: 0` es obligatorio.** licit analiza el historial git completo para trazabilidad de provenance. Un shallow clone produciría resultados incorrectos.

### Pipeline completo con reportes

```yaml
name: Compliance Pipeline

on:
  pull_request:
    branches: [main]

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install licit
        run: pip install licit-ai-cli

      - name: Track provenance
        run: licit trace

      - name: Generate compliance report
        run: licit report --format html -o compliance-report.html

      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: compliance-report
          path: compliance-report.html

      - name: Check gaps
        run: licit gaps

      - name: Verify compliance (gate)
        run: licit verify
```

### Evaluación por framework

```yaml
      # Solo EU AI Act
      - name: EU AI Act compliance
        run: licit verify --framework eu-ai-act

      # Solo OWASP
      - name: OWASP security posture
        run: licit verify --framework owasp

      # Ambos (default)
      - name: Full compliance
        run: licit verify --framework all
```

### Tratar PARTIAL como warning (no fallo)

```yaml
      - name: Compliance check
        run: |
          licit verify
          exit_code=$?
          if [ $exit_code -eq 1 ]; then
            echo "::error::Compliance check failed — non-compliant controls found"
            exit 1
          elif [ $exit_code -eq 2 ]; then
            echo "::warning::Compliance check partial — some controls need attention"
            exit 0  # No fallar en partial
          fi
```

---

## GitLab CI

```yaml
# .gitlab-ci.yml
compliance:
  image: python:3.12
  stage: test
  variables:
    GIT_DEPTH: 0  # Historial completo
  script:
    - pip install licit-ai-cli
    - licit trace
    - licit report --format json -o compliance.json
    - licit verify
  artifacts:
    paths:
      - compliance.json
    when: always
```

---

## Jenkins

```groovy
// Jenkinsfile
pipeline {
    agent { docker { image 'python:3.12' } }
    stages {
        stage('Compliance') {
            steps {
                checkout([$class: 'GitSCM',
                    extensions: [[$class: 'CloneOption', depth: 0, shallow: false]]])
                sh 'pip install licit-ai-cli'
                sh 'licit trace'
                sh 'licit report --format html -o compliance.html'
                sh 'licit verify'
            }
            post {
                always {
                    archiveArtifacts artifacts: 'compliance.html'
                }
            }
        }
    }
}
```

---

## Configuración por entorno

### Proyecto sin `.licit.yaml` previo

Si el pipeline corre en un proyecto que no tiene `.licit.yaml`, licit usa defaults (ambos frameworks habilitados). Esto funciona sin `licit init`:

```bash
licit verify  # Funciona sin init — usa defaults
```

### Versionar `.licit.yaml`

```bash
# En desarrollo local
licit init --framework eu-ai-act
git add .licit.yaml
git commit -m "chore: add licit configuration"
```

El pipeline usará la configuración versionada automáticamente.

### Paths que NO versionar

```gitignore
# .gitignore
.licit/provenance.jsonl
.licit/fria-data.json
.licit/.signing-key
```

Los reportes en `.licit/reports/` generalmente sí se pueden versionar — contienen evaluaciones, no datos sensibles.

---

## Estrategias de integración

### 1. Gate en PRs (recomendado)

```
PR abierto → licit verify → ¿pasa? → merge permitido
```

Configura branch protection en GitHub para requerir que el check de compliance pase antes de merge.

### 2. Report en cada release

```yaml
on:
  release:
    types: [published]

jobs:
  compliance-report:
    steps:
      - run: licit report --format html -o compliance-v${{ github.ref_name }}.html
      - uses: actions/upload-artifact@v4
        with:
          name: compliance-${{ github.ref_name }}
          path: compliance-*.html
```

### 3. Monitoreo periódico

```yaml
on:
  schedule:
    - cron: '0 9 * * 1'  # Lunes a las 9am

jobs:
  weekly-compliance:
    steps:
      - run: |
          licit trace
          licit report --format json -o weekly-report.json
          licit gaps
```

---

## Requisitos del entorno CI

| Requisito | Detalle |
|---|---|
| Python | 3.12+ |
| Git | Cualquier versión reciente |
| Historial git | Completo (`fetch-depth: 0`) |
| Disco | Mínimo — `.licit/` ocupa <1MB típicamente |
| Red | No requerida — licit es 100% offline |
| Permisos | Lectura del repositorio |

licit no hace llamadas de red, no requiere API keys, no envía datos a ningún servicio externo. Todo se ejecuta localmente.

---

## Troubleshooting CI/CD

### `licit verify` siempre falla

Probable causa: sin FRIA ni Annex IV, Art. 27 y Annex IV serán NON_COMPLIANT. Opciones:

1. Completar el FRIA: `licit fria` (interactivo, hacer en local)
2. Generar Annex IV: `licit annex-iv` (automático)
3. Evaluar solo OWASP: `licit verify --framework owasp`

### Provenance incorrecta

Si `licit trace` muestra 0 archivos o datos incorrectos, verifica que el checkout tiene historial completo:

```bash
git log --oneline | wc -l  # Debe ser > 0
```

### Pipeline lento

`licit trace` analiza todo el historial git. Para repos grandes, usa `--since`:

```yaml
- run: licit trace --since $(date -d '30 days ago' +%Y-%m-%d)
```
