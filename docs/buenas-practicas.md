# Buenas prácticas

Recomendaciones para integrar licit de forma efectiva en tu flujo de desarrollo con IA.

---

## Configuración inicial

### 1. Inicializa desde el principio

Ejecuta `licit init` al inicio del proyecto, no después. Cuanto antes empieces a rastrear, más completa será la evidencia de compliance.

```bash
mkdir mi-proyecto && cd mi-proyecto
git init
# ... setup inicial ...
licit init
git add .licit.yaml
git commit -m "feat: initialize licit compliance tracking"
```

### 2. Haz commit de `.licit.yaml`

El archivo de configuración debe estar versionado. Todo el equipo debe usar la misma configuración.

```bash
git add .licit.yaml
```

### 3. Configura `.gitignore` correctamente

```gitignore
# Datos sensibles de licit
.licit/provenance.jsonl
.licit/fria-data.json

# Clave de firmado
.licit/signing-key

# Reportes generados (opcional — pueden incluirse)
# .licit/reports/
```

### 4. Selecciona los frameworks relevantes

No habilites marcos que no aplican a tu contexto:

```yaml
# Si tu producto no opera en la UE:
frameworks:
  eu_ai_act: false
  owasp_agentic: true

# Si solo necesitas EU AI Act:
frameworks:
  eu_ai_act: true
  owasp_agentic: false
```

---

## Trazabilidad de provenance

### 5. Ejecuta `trace` regularmente

Ejecuta `licit trace` después de cada sprint o release para mantener la trazabilidad actualizada:

```bash
licit trace --since 2026-03-01 --stats --report
```

Combina heurísticas git con logs de sesión para mayor precisión:

```yaml
provenance:
  methods:
    - git-infer
    - session-log
  session_dirs:
    - ~/.claude/projects/
```

### 6. Habilita firmado en entornos regulados

Si necesitas demostrar integridad de la cadena de proveniencia:

```yaml
provenance:
  sign: true
  sign_key_path: ~/.licit/signing-key
```

Genera una clave segura:
```bash
python3.12 -c "import secrets; print(secrets.token_hex(32))" > ~/.licit/signing-key
chmod 600 ~/.licit/signing-key
```

### 7. Ajusta el umbral de confianza

El default (0.6) es conservador. Ajusta según tu contexto:

```yaml
provenance:
  # Más estricto (menos falsos positivos IA)
  confidence_threshold: 0.8

  # Más permisivo (detecta más código IA, más falsos positivos)
  confidence_threshold: 0.4
```

---

## Configuración de agentes IA

### 8. Documenta tus agentes

Mantén archivos de configuración de agentes explícitos:

```
CLAUDE.md              # Instrucciones para Claude Code
.cursorrules           # Reglas para Cursor
AGENTS.md              # Configuración de GitHub Agents
```

licit monitorea estos archivos automáticamente y registra cambios.

### 9. Implementa guardrails

En tu configuración de architect u otro agente, define:

- **Archivos protegidos**: Archivos que el agente no debe modificar.
- **Comandos bloqueados**: Comandos que el agente no debe ejecutar.
- **Reglas de código**: Patrones o prácticas obligatorias.

```yaml
# .architect/config.yaml (ejemplo)
guardrails:
  protected_files:
    - .env
    - secrets.yaml
    - migrations/
  blocked_commands:
    - rm -rf
    - DROP TABLE
  code_rules:
    - "no eval() or exec()"
    - "all API endpoints require authentication"
```

licit cuenta estos guardrails como evidencia de compliance.

### 10. Requiere revisión humana en CI/CD

Configura tu pipeline para requerir aprobación humana antes de deploy:

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    environment: production   # Requiere approval en GitHub
    steps:
      - name: Compliance check
        run: licit verify
      - name: Deploy
        run: ./deploy.sh
```

licit detecta la presencia de `environment:` en GitHub Actions como evidencia de human review gate.

---

## Compliance continuo

### 11. Integra `licit verify` en CI/CD

Añade una verificación de compliance en cada PR:

```yaml
# .github/workflows/compliance.yml
name: Compliance
on: [pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install licit-ai-cli
      - run: licit verify
```

### 12. Genera reportes periódicamente

No esperes a la auditoría. Genera reportes en cada release:

```bash
# Antes de cada release
licit trace --report
licit changelog
licit report --format markdown
git add .licit/reports/ .licit/changelog.md
git commit -m "docs: update compliance report for v1.2.0"
```

### 13. Revisa las brechas regularmente

```bash
licit gaps
```

Prioriza cerrar las brechas de mayor prioridad primero.

---

## Conectores

### 14. Habilita conectores cuando sea posible

Si usas Architect o Vigil, habilítalos. Aportan evidencia adicional:

```bash
licit connect architect
licit connect vigil
```

**Architect aporta:**
- Audit trail de ejecuciones
- Configuración de guardrails
- Quality gates

**Vigil aporta:**
- Hallazgos de seguridad (SARIF)
- SBOM (Software Bill of Materials)

### 15. Integra herramientas de seguridad

licit detecta automáticamente estas herramientas y usa sus resultados como evidencia:

| Herramienta | Qué detecta |
|---|---|
| Semgrep | Patrones de código inseguro |
| Snyk | Vulnerabilidades en dependencias |
| CodeQL | Análisis estático de seguridad |
| Trivy | Vulnerabilidades en containers |
| ESLint Security | Reglas de seguridad JavaScript |

---

## Organización del equipo

### 16. Designa un compliance lead

Alguien del equipo debe ser responsable de:
- Revisar reportes de licit periódicamente.
- Asegurar que las brechas se priorizan y cierran.
- Mantener actualizado el FRIA.
- Coordinar con legal/compliance si es necesario.

### 17. Documenta las decisiones

Cuando un requisito se marca como `n/a` (no aplica), documenta por qué. Esto es importante para auditorías:

```
# En tu FRIA o documentación interna:
Art. 10 (Data Governance): N/A — Este sistema no entrena modelos,
solo usa modelos pre-entrenados via API.
```

### 18. Mantén la configuración actualizada

Cuando cambies de herramienta de IA, actualiza la configuración:

```bash
# Tras migrar de Cursor a Claude Code
licit init  # Re-detecta el proyecto
licit status  # Verifica la detección
```

---

## Antipatrones a evitar

| Antipatrón | Por qué es problemático | Qué hacer en su lugar |
|---|---|---|
| Ignorar warnings de `licit verify` | Los parciales se acumulan | Tratar parciales como deuda técnica |
| No versionar `.licit.yaml` | Cada dev usa config diferente | Commit al repo |
| Subir `provenance.jsonl` a repo público | Expone info de contributors | Añadir a `.gitignore` |
| Generar reportes solo antes de auditorías | Evidencia incompleta | Generar en cada release |
| Deshabilitar el firmado "porque es lento" | Pérdida de integridad verificable | Firmar al menos en CI |
| No actualizar el FRIA | FRIA desactualizado no tiene valor | Actualizar con cada cambio significativo |
| Marcar todo como `n/a` | Evasión de compliance | Justificar cada `n/a` por escrito |
