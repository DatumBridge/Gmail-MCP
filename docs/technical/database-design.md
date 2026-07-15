# Database Design

## v1

No database. State is:

| Store | Location |
|-------|----------|
| OAuth pending tokens | In-memory (test UI connect) |
| User mailbox | Gmail (Google) |
| Operator token file | Local `token.json` (gitignored) |

If a future ADR adds encrypted tenant token storage, document schema here.
