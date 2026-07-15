# Security Architecture

```text
Studio (platform auth) → /mcp (FastMCP session) → tool
   → credentials_json/path (tenant token) → Gmail API
```

## Controls

| Concern | Control |
|---------|---------|
| Google access | User OAuth; scope `gmail.modify` |
| Tenant isolation | Credentials passed per call; no global default token |
| Secrets | Never log tokens / bodies; gitignore credentials |
| Attachments | Size cap via `GMAIL_MAX_ATTACHMENT_BYTES` |
| Prompt injection | Email content returned as untrusted data |
| Decisions | No authorize/approve tools |
| Prod `/mcp` | Front with Studio/gateway auth (session ≠ identity) |
| OAuth /test UI | Disabled in Docker by default (`GMAIL_ENABLE_OAUTH_UI=0`). Local connect requires cookie-bound state + TTL. Prefer `scripts/oauth_connect.py` in prod pipelines. |

See playbook `SECURITY_RULES.md` under the hub docs pack.
