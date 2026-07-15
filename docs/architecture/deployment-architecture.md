# Deployment Architecture

| Aspect | Practice |
|--------|----------|
| Runtime | `uvicorn app.mcp_server:http_app` port 8000 |
| Container | Multi-stage Python slim, non-root `appuser`, HEALTHCHECK `/health` |
| Secrets | OAuth client via env or mounted `credentials.json` (not baked into image) |
| Platform | Deploy via `datumbridge-deploy-service` like other MCP images |
| Ingress | Expose `/mcp/` and `/health`; OAuth callback must match console redirect URI |

Do not deploy WebSocket Services — this is not a relay.
