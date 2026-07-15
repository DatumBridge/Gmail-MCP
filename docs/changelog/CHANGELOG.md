# Changelog — Gmail MCP

## 2026-07-15

### Added

- Initial `gmail-mcp` tool-server: messages, threads, drafts, labels, attachments
- FastMCP Streamable HTTP `/mcp/`, `/health`, OAuth routes, test UI
- Docs governance tree + ADR-0001 / ADR-0002
- Helper unit tests (`scripts/test_helpers.py`)
- Production defaults: `GMAIL_ENABLE_OAUTH_UI=0` in Docker; cookie-bound OAuth state + TTL
- Attachment size gates before decode; `labels.patch` for partial label updates

### Changed

- N/A

### Fixed

- N/A

### Removed

- N/A
