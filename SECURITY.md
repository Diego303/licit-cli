# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.7.x   | :white_check_mark: |
| < 0.7   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in licit, please report it responsibly:

1. **Do NOT open a public issue.**
2. Email **security@licit.dev** (or open a private advisory on GitHub) with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)
3. You will receive an acknowledgment within 48 hours.
4. We aim to release a fix within 7 days for critical issues.

## Security Model

### What licit does

licit is a **read-only analysis tool** that:
- Reads git history via `git log`, `git show`, `git rev-list`
- Reads local configuration files (YAML, JSON, Markdown)
- Reads SARIF files and SBOM for security findings (via connectors)
- Reads architect reports, audit logs, and config YAML (via connectors)
- Writes output files to the `.licit/` directory
- Writes `.licit.yaml` configuration

### What licit does NOT do

- **No network access** — licit never makes HTTP requests, calls APIs, or phones home. All analysis is local.
- **No code execution** — licit does not execute, compile, or interpret analyzed code.
- **No credential handling** — licit does not read, store, or transmit secrets, API keys, or credentials.
- **No elevated privileges** — licit runs entirely in userspace with no special permissions.
- **Connectors are read-only** — architect and vigil connectors only read files; they never execute external tools or modify data.

### Threat Model

| Threat | Severity | Mitigation |
|--------|----------|------------|
| Malicious `.licit.yaml` config | Low | Pydantic v2 validation rejects unexpected types. `yaml.safe_load` only (no code execution). |
| Malicious SARIF/JSON files | Low | `json.loads` only. No eval or dynamic execution. All fields validated with `isinstance`. |
| Path traversal in config paths | Low | All file paths resolved relative to project root. No absolute path injection. |
| Git command injection | Low | All subprocess calls use list-form arguments (no `shell=True`). Explicit timeouts (10-30s). `check=False` throughout. |
| Provenance store tampering | High | HMAC-SHA256 signatures on records (when signing enabled). Merkle tree for batch integrity. Append-only JSONL. |
| Sensitive data in FRIA | Medium | `fria-data.json` should be in `.gitignore`. Not committed to public repos. |
| Sensitive data in provenance | Medium | `provenance.jsonl` contains contributor names. Add to `.gitignore`. |
| Signing key exposure | High | `.licit/.signing-key` must never be committed. Permissions should be `600`. |

### Cryptographic Operations

licit uses cryptography for provenance attestation:
- **Algorithm**: HMAC-SHA256 for individual record signing
- **Batch integrity**: SHA-256 Merkle tree for batch verification
- **Key storage**: `.licit/.signing-key` (auto-generated 256-bit key via `os.urandom(32)`)
- **Key resolution**: explicit `sign_key_path` → `.licit/.signing-key` → auto-generate
- **Verification**: timing-safe via `hmac.compare_digest`
- **Future (V1)**: Sigstore/cosign integration for keyless signing

**Important**: The `.licit/.signing-key` file should be added to `.gitignore` and never committed to version control.

### Subprocess Execution

licit executes git commands via `subprocess.run()` with these protections:

- `capture_output=True` — stdout/stderr captured, not displayed
- `text=True` — UTF-8 decoding
- No `shell=True` — arguments passed as list, preventing command injection
- `timeout=30` — explicit timeout (10s for `git show`, 30s for `git log`)
- `check=False` — does not raise on non-zero exit codes
- Size guard: `_MAX_CONTENT_BYTES = 1_048_576` on `git show` output to prevent OOM

### Dependencies

licit uses 6 runtime dependencies, all well-maintained:

| Dependency | Purpose | Security Notes |
|------------|---------|----------------|
| click | CLI framework | No network, no eval |
| pydantic | Config validation | Strict validation, no arbitrary execution |
| structlog | Structured logging | Output only, no side effects |
| pyyaml | YAML parsing | Uses `safe_load` exclusively |
| jinja2 | Report templates | Sandboxed by default, templates are local only |
| cryptography | HMAC signing | Industry-standard, FIPS-validated implementations |

### Recommended `.gitignore` Entries

```gitignore
# licit — sensitive data
.licit/.signing-key
.licit/provenance.jsonl
.licit/fria-data.json

# licit — generated reports (optional — may want to commit these)
# .licit/reports/
# .licit/fria-report.md
# .licit/annex-iv.md
```

## Security Best Practices for Users

1. **Review `.licit.yaml` before committing** — Ensure no sensitive paths or credentials are included.
2. **Add `.licit/.signing-key` to `.gitignore`** — Signing keys should not be in version control.
3. **Add `.licit/fria-data.json` to `.gitignore`** — FRIA data may contain sensitive assessment details.
4. **Run `licit verify` in CI/CD** — Use the exit code gate to catch compliance regressions.
5. **Keep dependencies updated** — Run `pip install --upgrade licit-ai-cli` regularly.
6. **Review provenance reports** — Audit AI-generated code attributions for accuracy.
7. **Use signing in regulated environments** — Enable `provenance.sign: true` for tamper evidence.

## Detailed Security Documentation

For in-depth security documentation (threat model detail, Merkle tree diagrams, parsing safety, subprocess protections), see [docs/seguridad.md](docs/seguridad.md).
