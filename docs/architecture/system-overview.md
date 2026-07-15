# System Overview — Gmail MCP

## Role

`gmail-mcp` is a DatumBridge **MCP tool-server** for Gmail. Studio / LangGraph call tools over Streamable HTTP (`POST {baseURL}/mcp/`).

## What changed

| Area | Change |
|------|--------|
| New service | Full Gmail tool surface (messages, threads, drafts, labels, attachments) |
| OAuth | Pass-through credentials per call + web/CLI connect flow |

## Impacted components

- DatumBridge Tool Registry (`mcpServer=gmail`)
- Studio MCP tool nodes / LangGraph binders

## Dependencies

- Google Gmail API
- OAuth client credentials
- FastMCP + google-api-python-client

## Risks

- Restricted Gmail scopes may require Google verification for production tenants
- Attachment size / memory on large MIME payloads
- Permanent delete needs broader scope than default `gmail.modify`
