# Integrations

## Google Gmail API

- Endpoint builder: `googleapiclient.discovery.build("gmail", "v1", …)`
- User: `me`
- Scope: `https://www.googleapis.com/auth/gmail.modify`

## DatumBridge Tool Registry

- Discover via `initialize` → `tools/list`
- Store `mcpServer=gmail` and base URL ending in `/mcp/` or host that appends `/mcp`
- Each tool input schema carries `x-datumbridge-docs` (markdown from `registry_docs/<tool>.md`) and `x-datumbridge-capabilities`. Setup/publish moves Docs off the stored schema onto the tool Docs field so the planner catalog can use it without embedding the full guide in the JSON Schema.

## Sibling services

| Service | Overlap |
|---------|---------|
| `google-drive-mcp` | Same OAuth pass-through pattern |
| `datumbridge-mcp-ws-hub` | Not used; wrong class for Gmail |

## Out of scope

WS device registry, edge catalogs, IMAP/SMTP direct.
