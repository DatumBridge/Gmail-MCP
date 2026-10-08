# Workflows

## Connect

1. Operator opens `/test` → Connect with Google, or runs `scripts/oauth_connect.py`
2. Token stored locally (`token.json` / localStorage)
3. Tools receive token via `credentials_json` or `credentials_path`

## Agent call

1. Platform initializes MCP session on `/mcp/`
2. `tools/list` includes `x-datumbridge-docs` from `registry_docs/<tool>.md`. Setup copies that markdown onto the tool Docs field.
3. Deep Agent reads the parameter Sample column and the error-code table, then `tools/call` with user-supplied args only (no invented `credentials_json`).
4. On `success: false`, Deep reads `error.error_code` and retries only when `retryable` is true (`AUTH_ERROR` once; `RATE_LIMIT` / `PROVIDER_ERROR` at most three times). Missing required args are JSON-RPC `-32602`, not that envelope.

## Reply

1. `get_message` → inspect headers/body (untrusted)
2. `reply_message` with `message_id` + body
3. Service sets `In-Reply-To` / `References` / `threadId`
