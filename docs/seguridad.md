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

En fases futuras, licit implementará un Merkle tree sobre el provenance store para detectar manipulación o eliminación de registros:

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
- Timeout implícito en operaciones de red (futuro).

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
