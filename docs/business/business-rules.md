# Business Rules

1. Service class is **tool-server**.
2. Every tool requires OAuth credentials input.
3. Missing credentials → `CREDENTIALS_REQUIRED` (fail-fast).
4. Prefer `trash_*` over permanent `delete_*`.
5. Tools return mailbox data; they do not make workflow decisions.
6. Attachment oversize → `VALIDATION_ERROR`.
7. Rate/quota 429 → `RATE_LIMIT`, `retryable: true`.
8. Do not advertise resources/prompts unless implemented.
9. Each tool's Deep Agent guide in `registry_docs/<tool>.md` MUST include: when to call, a parameter table with **Sample** values, success field samples, the full `error_code` set, and at least one success case. Codes MUST match `DOCUMENTED_ERROR_CODES` in `app/core/exceptions.py` (exception classes plus credential/provider literals). Do not document a non-Gmail code such as `invalid_argument`. Missing required args are MCP JSON-RPC `-32602`, not a fake `VALIDATION_ERROR` envelope.
10. Deep Agent MUST NOT invent Gmail IDs, OAuth tokens, or placeholder emails. IDs come from a prior Gmail tool result; recipients come from the user or from `get_message` headers.
