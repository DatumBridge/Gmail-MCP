# Workflows

## Connect

1. Operator opens `/test` → Connect with Google, or runs `scripts/oauth_connect.py`
2. Token stored locally (`token.json` / localStorage)
3. Tools receive token via `credentials_json` or `credentials_path`

## Agent call

1. Platform initializes MCP session on `/mcp/`
2. `tools/list` then `tools/call` with credentials + args
3. Service maps result or structured error

## Reply

1. `get_message` → inspect headers/body (untrusted)
2. `reply_message` with `message_id` + body
3. Service sets `In-Reply-To` / `References` / `threadId`
