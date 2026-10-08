# System Overview — Gmail MCP

## Role

`gmail-mcp` is a DatumBridge **MCP tool-server** for Gmail. Studio / LangGraph call tools over Streamable HTTP (`POST {baseURL}/mcp/`).

## What changed

| Area | Change | Why | Impacted components | Risks |
|------|--------|-----|---------------------|-------|
| Tool Docs | Each MCP tool ships a Deep Agent guide in `registry_docs/<tool>.md` (parameter samples, error codes, cases). Bound as `x-datumbridge-docs`. | Generic generated docs omitted Gmail `error_code` values and per-property samples, so Deep Agent guessed arguments. | Tool Registry Docs field, Deep planner catalog after Setup/publish | Low — display/planning text only. Redeploy `gmail-mcp` then Setup or publish. |
| New service | Full Gmail tool surface (messages, threads, drafts, labels, attachments) | Product | DatumBridge Tool Registry (`mcpServer=gmail`) | Restricted Gmail scopes |
| OAuth | Pass-through credentials per call + web/CLI connect flow | Tenant isolation | Studio Integrations vault | Token handling |

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
