# Changelog — Gmail MCP

## 2026-10-08

### Added

- Per-tool Deep Agent guides in `registry_docs/<tool>.md`: parameter sample column, success field samples, `DOCUMENTED_ERROR_CODES`, untrusted-mailbox rules, and input/output cases. Regenerated with `python3 scripts/generate_registry_docs.py`.

### Changed

- Tool Registry Docs import (`x-datumbridge-docs`) now ships the Gmail-specific guides instead of the generic typical-call stub (which used a non-Gmail `invalid_argument` code).

### Fixed

- N/A

### Removed

- N/A

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
