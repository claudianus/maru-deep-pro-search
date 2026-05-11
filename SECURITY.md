# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.9.x   | ✅ Active development |
| < 0.9.0 | ❌ No longer supported |

## Reporting a Vulnerability

If you discover a security vulnerability in `maru-deep-pro-search`, please report it responsibly:

1. **Do NOT open a public issue.**
2. Email **claudianus@github.com** with:
   - A clear description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested fix (if any)

You can expect:
- An acknowledgment within 48 hours
- A detailed response within 7 days
- Credit in the changelog upon resolution (unless you prefer anonymity)

## Security Features

This project implements multiple defense layers:

- **72 prompt injection signatures** covering 10+ languages
- **MCP-specific attack detection**: tool poisoning, rug pulls, shadowing, MPMA
- **Content sanitization**: zero-width character stripping, token neutralization
- **Audit logging**: behavioral anomaly detection for tool invocations
- **Docker sandbox**: isolated execution environment

## Known Limitations

- Search results depend on the security posture of scraped websites
- Semantic embedding models run locally (CPU-only) — no external API calls
- Audit logs are stored locally in SQLite; rotate `.maru/audit.db` periodically
