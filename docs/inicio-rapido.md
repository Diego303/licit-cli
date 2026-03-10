# Inicio rápido

Guía para tener licit funcionando en tu proyecto en 5 minutos.

---

## 1. Instalar

```bash
pip install licit-ai-cli
```

> Requiere Python 3.12+. Si tienes varias versiones: `python3.12 -m pip install licit-ai-cli`

Verifica:
```bash
licit --version
# licit, version 0.1.0
```

---

## 2. Inicializar

Entra al directorio de tu proyecto y ejecuta:

```bash
cd mi-proyecto/
licit init
```

Esto:
- Detecta automáticamente lenguajes, frameworks, CI/CD, agentes IA y herramientas de seguridad.
- Genera `.licit.yaml` con la configuración adaptada.
- Crea el directorio `.licit/` para datos internos.

```
Initialized licit in mi-proyecto
  Languages: python
  Frameworks: fastapi
  Agent configs: CLAUDE.md
  CI/CD: github-actions
  Config saved to .licit.yaml
```

Si solo necesitas un marco regulatorio específico:
```bash
licit init --framework eu-ai-act     # Solo EU AI Act
licit init --framework owasp         # Solo OWASP Agentic Top 10
```

---

## 3. Ver estado

```bash
licit status
```

Muestra un resumen de:
- Proyecto detectado (nombre, lenguajes, frameworks, git)
- Configuración cargada
- Frameworks habilitados
- Fuentes de datos disponibles
- Conectores activos
- Configuraciones de agentes IA encontradas

---

## 4. Conectar fuentes de datos (opcional)

Si usas Architect o Vigil:

```bash
licit connect architect    # Lee reports y audit logs de Architect
licit connect vigil        # Lee hallazgos SARIF de Vigil
```

Para desconectar:
```bash
licit connect architect --disable
```

---

## 5. Versionar la configuración

```bash
git add .licit.yaml
git commit -m "chore: initialize licit compliance tracking"
```

Añade a `.gitignore` los datos sensibles:
```gitignore
.licit/provenance.jsonl
.licit/fria-data.json
.licit/signing-key
```

---

## ¿Qué sigue?

Una vez completadas las fases futuras de licit, podrás:

```bash
# Rastrear proveniencia del código (IA vs humano)
licit trace --stats

# Generar changelog de configs de agentes
licit changelog

# Completar evaluación de impacto (FRIA)
licit fria

# Generar documentación técnica Annex IV
licit annex-iv --organization "Mi Empresa" --product "Mi App"

# Ver reporte de compliance
licit report

# Identificar brechas
licit gaps

# Gate de CI/CD (exit code 0 = pass)
licit verify
```

---

## Estructura generada

Después de `licit init`, tu proyecto tendrá:

```
mi-proyecto/
├── .licit.yaml          # Configuración (versionar)
├── .licit/              # Datos internos
│   ├── provenance.jsonl # Trazabilidad (NO versionar)
│   ├── changelog.md     # Changelog de configs
│   ├── fria-data.json   # Datos FRIA (NO versionar)
│   ├── fria-report.md   # Reporte FRIA
│   ├── annex-iv.md      # Documentación Annex IV
│   └── reports/         # Reportes generados
└── ... tu código ...
```

---

## Referencia rápida de comandos

| Comando | Qué hace |
|---|---|
| `licit init` | Inicializa licit en el proyecto |
| `licit status` | Muestra estado y fuentes conectadas |
| `licit connect <nombre>` | Habilita/deshabilita un conector |
| `licit trace` | Rastrea proveniencia del código |
| `licit changelog` | Genera changelog de configs de agentes |
| `licit fria` | Evaluación de impacto en derechos fundamentales |
| `licit annex-iv` | Documentación técnica EU AI Act |
| `licit report` | Reporte unificado de compliance |
| `licit gaps` | Identifica brechas de compliance |
| `licit verify` | Gate CI/CD (exit 0/1/2) |

Opciones globales: `--version`, `--config PATH`, `--verbose`, `--help`

---

Para más detalle, consulta la [documentación completa](README.md).
