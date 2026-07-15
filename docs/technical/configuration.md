# Configuration

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `PORT` | no | `8000` (uvicorn CLI) | Listen port |
| `LOG_LEVEL` | no | INFO | Logging |
| `GOOGLE_OAUTH_CREDENTIALS` | no | `./credentials.json` | OAuth client file |
| `GOOGLE_OAUTH_CLIENT_ID` | alt | — | Client id |
| `GOOGLE_OAUTH_CLIENT_SECRET` | alt | — | Client secret |
| `OAUTH_REDIRECT_URI` | no | derived | Exact console redirect |
| `GMAIL_MAX_ATTACHMENT_BYTES` | no | `26214400` | Attachment cap |
| `GMAIL_ENABLE_OAUTH_UI` | no | `1` locally; **`0` in Docker image** | Gate `/oauth/*` and `/test`. Production images keep off; use `scripts/oauth_connect.py` or Studio-managed tokens. |
| `TOOL_REGISTRY_BASE_URL` | no | — | Optional registry |
| `TOOL_REGISTRY_API_KEY` | no | — | Registry auth |

Never commit `.env`, `credentials.json`, or `token.json`.
