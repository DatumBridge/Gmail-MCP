# Component Diagram

```text
┌─────────────────────────────────────────────┐
│              app/mcp_server.py              │
│  FastMCP tools + Starlette (/health,/oauth) │
└────────────────────┬────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
  oauth_routes.py         GmailService
  (consent + token)    (gmail_service.py)
                                 │
                                 ▼
                           Gmail API v1
```

Supporting: `core/exceptions.py`, `schemas/mcp_models.py`, `registry_docs/<tool>.md` (bound as `x-datumbridge-docs`).
