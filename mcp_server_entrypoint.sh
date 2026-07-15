#!/bin/bash
# Entrypoint for running Gmail MCP Server in HTTP/SSE mode
# Usage: ./mcp_server_entrypoint.sh

cd "$(dirname "$0")"
uvicorn app.mcp_server:http_app --host 0.0.0.0 --port 8000
