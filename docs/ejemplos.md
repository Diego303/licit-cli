# Ejemplos y recetas

Flujos de trabajo completos para casos de uso comunes.

---

## 1. Equipo nuevo que empieza a usar agentes IA

**Contexto**: Tu equipo va a empezar a usar Claude Code. Quieres compliance desde el día uno.

```bash
# Inicializar
cd mi-proyecto/
licit init

# Configurar firmado de provenance
cat >> .licit.yaml << 'EOF'
provenance:
  sign: true
  methods:
    - git-infer
    - session-log
EOF

# Primer baseline
licit trace --stats --report
licit report --format html -o .licit/reports/baseline.html
licit gaps

# Versionar
git add .licit.yaml .licit/reports/baseline.html
git commit -m "chore: initialize licit compliance tracking"
```

---

## 2. Proyecto existente preparándose para auditoría EU AI Act

**Contexto**: Tienes un proyecto con 6 meses de historial git, CLAUDE.md configurado, y necesitas documentación EU AI Act.

```bash
# Inicializar y analizar
licit init --framework eu-ai-act
licit trace --stats

# Generar documentación regulatoria
licit fria                    # Cuestionario interactivo (local)
licit fria --auto             # Modo no-interactivo (CI/CD)
licit annex-iv --organization "Mi Empresa" --product "Mi App v2"

# Evaluar estado
licit report --format html -o compliance-report.html
licit gaps --framework eu-ai-act

# Verificar antes de auditoría
licit verify --framework eu-ai-act
echo "Exit code: $?"
```

**Entregables para el auditor:**
- `.licit/fria-report.md` — FRIA completado
- `.licit/annex-iv.md` — Documentación técnica Annex IV
- `compliance-report.html` — Reporte de compliance con evidencia
- `.licit/provenance-report.md` — Trazabilidad AI vs humano

---

## 3. CI/CD gate con compliance progresivo

**Contexto**: No quieres bloquear PRs por compliance al principio, pero sí tener visibilidad. Transición gradual de warning a blocking.

**Fase 1 — Solo reportar (no bloquea):**

```yaml
# .github/workflows/compliance.yml
name: Compliance
on: [pull_request]

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install licit-ai-cli
      - name: Compliance report
        run: |
          licit report --format json -o compliance.json
          licit gaps
        continue-on-error: true      # No bloquea PR
      - uses: actions/upload-artifact@v4
        with:
          name: compliance-report
          path: compliance.json
```

**Fase 2 — Warning en parcial, block en non-compliant:**

```yaml
      - name: Compliance gate
        run: |
          licit verify
          EXIT=$?
          if [ $EXIT -eq 1 ]; then
            echo "::error::Non-compliant — fix required"
            exit 1
          elif [ $EXIT -eq 2 ]; then
            echo "::warning::Partially compliant — review recommended"
            exit 0   # No bloquea, solo warning
          fi
```

**Fase 3 — Full blocking:**

```yaml
      - name: Compliance gate
        run: licit verify   # Bloquea en exit 1 o 2
```

---

## 4. Monorepo con múltiples servicios

**Contexto**: Un monorepo con 3 servicios, cada uno con su propio agente config.

```
monorepo/
├── services/
│   ├── api/          ← Python + Claude Code
│   ├── frontend/     ← TypeScript + Cursor
│   └── worker/       ← Go + Copilot
├── CLAUDE.md
└── .cursorrules
```

```bash
# Inicializar cada servicio
for svc in api frontend worker; do
  (cd services/$svc && licit init)
done

# O inicializar desde la raíz (analiza todo el monorepo como un proyecto)
cd monorepo/
licit init
licit trace --stats
```

---

## 5. Conectar architect para evidencia completa

**Contexto**: Usas architect como agente de codificación. Quieres que licit lea sus outputs.

```bash
# 1. Habilitar conector
licit connect architect
# → architect data found at: .architect/reports
# → Connector 'architect' enabled.

# 2. Configurar audit log (si architect lo genera)
cat >> .licit.yaml << 'EOF'
connectors:
  architect:
    enabled: true
    config_path: .architect/config.yaml
    audit_log: .architect/audit.jsonl
EOF

# 3. Verificar que la evidencia se enriquece
licit status
# → Connectors:
# →   [x] architect (.architect/config.yaml, enabled)

# 4. El reporte ahora refleja guardrails y audit trail
licit report
licit gaps
```

---

## 6. Script de compliance periódico

**Contexto**: Generar reportes de compliance en cada release.

```bash
#!/bin/bash
# scripts/compliance-report.sh
set -e

VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "dev")
DATE=$(date +%Y-%m-%d)

echo "Generating compliance report for $VERSION..."

# Actualizar provenance
licit trace --since "$(git log --format=%aI -1 HEAD~50)" --report

# Generar changelog de configs
licit changelog

# Generar reportes en 3 formatos
licit report --format markdown -o ".licit/reports/compliance-$VERSION.md"
licit report --format json -o ".licit/reports/compliance-$VERSION.json"
licit report --format html -o ".licit/reports/compliance-$VERSION.html"

# Gap analysis
licit gaps > ".licit/reports/gaps-$VERSION.txt" 2>&1 || true

# Commit
git add .licit/reports/ .licit/changelog.md
git commit -m "docs: compliance report for $VERSION ($DATE)" || true

echo "Done. Reports in .licit/reports/"
```

---

## 7. Comparar compliance entre releases

**Contexto**: Quieres ver si el compliance mejoró entre v1.0 y v1.1.

```bash
# Generar reporte V1.0
git checkout v1.0
licit report --format json -o /tmp/compliance-v1.0.json

# Generar reporte V1.1
git checkout v1.1
licit report --format json -o /tmp/compliance-v1.1.json

# Comparar (con jq)
echo "=== V1.0 ===" && jq '.overall.compliance_rate' /tmp/compliance-v1.0.json
echo "=== V1.1 ===" && jq '.overall.compliance_rate' /tmp/compliance-v1.1.json

# Diff detallado
diff <(jq '.frameworks[].results[] | {id: .requirement.id, status: .status}' /tmp/compliance-v1.0.json) \
     <(jq '.frameworks[].results[] | {id: .requirement.id, status: .status}' /tmp/compliance-v1.1.json)
```
