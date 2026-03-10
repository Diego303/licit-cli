# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | :white_check_mark: |

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
- Reads SARIF files for security findings
- Writes output files to the `.licit/` directory
- Writes `.licit.yaml` configuration

### What licit does NOT do

- **No network access** — licit never makes HTTP requests, calls APIs, or phones home. All analysis is local.
- **No code execution** — licit does not execute, compile, or interpret analyzed code.
- **No credential handling** — licit does not read, store, or transmit secrets, API keys, or credentials.
- **No elevated privileges** — licit runs entirely in userspace with no special permissions.

### Threat Model

| Threat | Mitigation |
|--------|------------|
| Malicious `.licit.yaml` config | Pydantic v2 validation rejects unexpected fields. Config parsing uses `yaml.safe_load` (no arbitrary code execution). |
| Malicious SARIF files | JSON parsing with `json.loads` only. No eval or dynamic execution. |
| Path traversal in config paths | All file paths are resolved relative to project root. No absolute path injection. |
| Git command injection | All git subprocess calls use list-form arguments (no shell interpolation). Timeouts prevent hangs. |
| Provenance store tampering | HMAC-SHA256 signatures on provenance records (when signing is enabled). Append-only JSONL format. |
| Sensitive data in reports | Reports only contain metadata (file names, compliance status, timestamps). No source code content is included in reports. |

### Cryptographic Operations

licit uses cryptography for provenance attestation (Phase 2):
- **Algorithm**: HMAC-SHA256 for record signing
- **Key storage**: `.licit/.signing-key` (auto-generated 256-bit key)
- **Merkle trees**: SHA-256 hash chains for batch integrity
- **Future (V1)**: Sigstore/cosign integration for keyless signing

**Important**: The `.licit/.signing-key` file should be added to `.gitignore` and never committed to version control.

### Dependencies

licit uses a minimal dependency set, all from well-maintained PyPI packages:

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
# licit sensitive files
.licit/.signing-key
.licit/provenance.jsonl

# licit generated reports (optional — may want to commit these)
# .licit/reports/
# .licit/fria-report.md
# .licit/annex-iv.md
```

## Security Best Practices for Users

1. **Review `.licit.yaml` before committing** — Ensure no sensitive paths or credentials are included.
2. **Add `.licit/.signing-key` to `.gitignore`** — Signing keys should not be in version control.
3. **Run `licit verify` in CI/CD** — Use the exit code gate to catch compliance regressions.
4. **Keep dependencies updated** — Run `pip install --upgrade licit-ai-cli` regularly.
5. **Review provenance reports** — Audit AI-generated code attributions for accuracy.
