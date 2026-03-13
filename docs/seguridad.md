# Seguridad

## Modelo de amenazas

licit opera como una herramienta de auditoría local. Su superficie de ataque es limitada, pero existen riesgos a considerar:

### Amenazas identificadas

| Amenaza | Severidad | Mitigación |
|---|---|---|
| Manipulación de provenance store | Alta | Firmado HMAC-SHA256, Merkle tree de integridad |
| Datos sensibles en FRIA | Media | `.gitignore` para `fria-data.json`, no subir a repos públicos |
| Inyección vía YAML malicioso | Baja | Uso exclusivo de `yaml.safe_load()` (no `yaml.load()`) |
| Dependencias comprometidas | Media | Auditoría periódica, pinning de versiones mínimas |
| Ejecución de código vía configs | Baja | No se ejecuta código de configs; solo se parsean datos |
| Exposición de info de contributors | Baja | Provenance no se sube por defecto; recomendación en `.gitignore` |

### Qué NO hace licit

- **No ejecuta código arbitrario** de los archivos que analiza.
- **No envía datos a servidores externos**. Todo se procesa localmente.
- **No requiere permisos elevados**. Opera con los permisos del usuario.
- **No modifica el código fuente** del proyecto analizado.
- **No almacena credenciales**. Las claves de firmado las gestiona el usuario.

---

## Firmado criptográfico (provenance)

### HMAC-SHA256

Cuando se habilita el firmado de provenance (`provenance.sign: true`), cada registro se firma con HMAC-SHA256:

```
signature = HMAC-SHA256(key, canonical_json(record))
```

**Configuración:**
```yaml
provenance:
  sign: true
  sign_key_path: ~/.licit/signing-key
```

**Generación de clave:**
```bash
# Generar una clave de 256 bits
python3.12 -c "import secrets; print(secrets.token_hex(32))" > ~/.licit/signing-key
chmod 600 ~/.licit/signing-key
```

### Attestation (Merkle tree)

licit implementa un Merkle tree sobre los registros de provenance para detectar manipulación:

```
         root_hash
        /         \
    hash_01      hash_23
    /    \       /    \
 hash_0 hash_1 hash_2 hash_3
   |      |      |      |
 rec_0  rec_1  rec_2  rec_3
```

Cualquier modificación de un registro invalida la cadena de hashes desde ese registro hasta la raíz.

**Implementación**:
- Cada record se serializa como JSON canónico (`sort_keys=True, default=str`)
- Se calcula SHA256 de cada record → hojas del árbol
- Pares de hashes se concatenan y re-hashean hasta obtener la raíz
- Registros impares: el último se duplica para completar el par
- La verificación individual usa `hmac.compare_digest` (timing-safe)

```python
from licit.provenance.attestation import ProvenanceAttestor

attestor = ProvenanceAttestor()  # Auto-genera key en .licit/.signing-key

# Firmar un registro individual
sig = attestor.sign_record({"file": "app.py", "source": "ai"})

# Verificar integridad
assert attestor.verify_record({"file": "app.py", "source": "ai"}, sig)

# Firmar batch con Merkle tree
root = attestor.sign_batch([record1, record2, record3])
```

### Key management

La clave de firmado se resuelve en este orden:

1. **Path explícito** (`sign_key_path` en config)
2. **Fallback local** (`.licit/.signing-key` en el proyecto)
3. **Auto-generación** (32 bytes aleatorios con `os.urandom(32)`)

Todos los accesos a filesystem están protegidos con `try/except OSError`.

---

## Protección de datos

### Datos sensibles generados por licit

| Archivo | Sensibilidad | Recomendación |
|---|---|---|
| `.licit.yaml` | Baja | Commit al repo |
| `.licit/provenance.jsonl` | Media | No commit (contiene info de contributors) |
| `.licit/fria-data.json` | Alta | No commit (datos de impacto en derechos) |
| `.licit/fria-report.md` | Media | Commit selectivo |
| `.licit/annex-iv.md` | Baja | Commit al repo |
| `.licit/changelog.md` | Baja | Commit al repo |
| `.licit/reports/*` | Baja | Commit al repo |
| Clave de firmado | Crítica | Nunca commit, permisos 600 |

### .gitignore recomendado

```gitignore
# licit — datos sensibles
.licit/provenance.jsonl
.licit/fria-data.json

# licit — clave de firmado (si se almacena en el proyecto)
.licit/signing-key
*.key

# licit — reportes generados (opcional, pueden hacer commit)
# .licit/reports/
```

---

## Dependencias

### Auditoría de dependencias

licit usa 6 dependencias de runtime, todas ampliamente adoptadas:

| Dependencia | Versión mín. | Propósito | Mantenedor |
|---|---|---|---|
| click | 8.1+ | Framework CLI | Pallets |
| pydantic | 2.0+ | Validación de config | Samuel Colvin |
| structlog | 24.1+ | Logging estructurado | Hynek Schlawack |
| pyyaml | 6.0+ | Parsing YAML | YAML org |
| jinja2 | 3.1+ | Templates de reportes | Pallets |
| cryptography | 42.0+ | HMAC-SHA256 | PyCA |

### Recomendaciones

1. **Pinear versiones en producción**: Usar un `requirements.txt` o `pip-compile` para lockear versiones exactas.

2. **Auditar regularmente**:
   ```bash
   pip audit                    # Busca vulnerabilidades conocidas
   pip install pip-audit && pip-audit  # Alternativa
   ```

3. **Verificar hashes**:
   ```bash
   pip install --require-hashes -r requirements.txt
   ```

---

## Parsing seguro de archivos

### YAML

licit **siempre** usa `yaml.safe_load()` para parsear YAML. Nunca `yaml.load()` (que permite ejecución arbitraria de código Python).

```python
# Correcto (lo que hace licit)
data = yaml.safe_load(f.read())

# NUNCA (vulnerable a ejecución de código)
# data = yaml.load(f.read(), Loader=yaml.FullLoader)
```

### JSON

Para SARIF y otros archivos JSON, se usa `json.load()` estándar, que es seguro por diseño.

### Archivos de configuración de agentes

Los archivos como `CLAUDE.md`, `.cursorrules`, `AGENTS.md` se leen como texto plano. licit **no interpreta ni ejecuta** su contenido — solo lo analiza para detectar cambios y extraer metadatos.

---

## Ejecución de procesos externos

licit ejecuta comandos git mediante `subprocess.run()` con las siguientes protecciones:

- `capture_output=True` — stdout/stderr capturados, no mostrados directamente.
- `text=True` — Decodificación UTF-8 automática.
- Sin `shell=True` — Los argumentos se pasan como lista, no como string, previniendo inyección de comandos.
- `timeout=30` — Timeout explícito de 30 segundos en `git log` para evitar bloqueos en repos masivos (10 segundos para `git show` y verificaciones de existencia).
- `subprocess.TimeoutExpired` capturado — retorna lista vacía sin crashear.
- `check=False` explícito — en todos los `subprocess.run` de provenance y changelog (no lanza excepción en returncode != 0).
- **Size guard (changelog)**: `ConfigWatcher._MAX_CONTENT_BYTES = 1_048_576` — descarta contenido de `git show` superior a 1 MB para prevenir OOM con archivos binarios accidentalmente tracked.

```python
# Así ejecuta licit los comandos git
result = subprocess.run(
    ["git", "rev-list", "--count", "HEAD"],
    capture_output=True,
    text=True,
)
```

---

## Reporte de vulnerabilidades

Si encuentras una vulnerabilidad de seguridad en licit:

1. **No abras un issue público.**
2. Envía un email a los mantenedores con:
   - Descripción de la vulnerabilidad
   - Pasos para reproducir
   - Impacto potencial
3. Recibirás una confirmación en 48 horas.
4. Se publicará un fix y un advisory una vez resuelto.

Ver [SECURITY.md](../SECURITY.md) en la raíz del proyecto para información de contacto.
