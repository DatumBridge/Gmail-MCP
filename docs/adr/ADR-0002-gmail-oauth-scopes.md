# ADR-0002 — Gmail OAuth Scopes

## Context

Full Gmail features need read, send, drafts, labels, and trash. Permanent delete needs broader access.

## Decision

Default scope:

```text
https://www.googleapis.com/auth/gmail.modify
```

Prefer `trash_message` / `trash_thread`. Permanent `delete_*` may fail until the operator re-consents with `https://mail.google.com/` — document explicitly rather than requesting full mail scope by default.

## Alternatives Considered

| Scope | Trade-off |
|-------|-----------|
| `mail.google.com` | Simplest “full” access; high sensitivity / verification burden |
| `gmail.readonly` + `gmail.send` | More tokens; split capabilities |
| `gmail.modify` (chosen) | Covers v1 tools with least privilege for trash-first workflows |

## Consequences

- OAuth consent screens request modify only
- Permanent delete is best-effort under default consent

## Risks

Google restricted-scope verification for production multi-tenant apps.
