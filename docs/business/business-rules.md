# Business Rules

1. Service class is **tool-server**.
2. Every tool requires OAuth credentials input.
3. Missing credentials → `CREDENTIALS_REQUIRED` (fail-fast).
4. Prefer `trash_*` over permanent `delete_*`.
5. Tools return mailbox data; they do not make workflow decisions.
6. Attachment oversize → `VALIDATION_ERROR`.
7. Rate/quota 429 → `RATE_LIMIT`, `retryable: true`.
8. Do not advertise resources/prompts unless implemented.
