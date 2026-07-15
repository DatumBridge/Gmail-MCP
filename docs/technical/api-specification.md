# API Specification — Gmail MCP

## HTTP

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | `{"status":"ok","service":"gmail-mcp"}` |
| GET | `/test` | Manual test UI — **404 unless** `GMAIL_ENABLE_OAUTH_UI=1` |
| GET | `/oauth/start` | Start Google consent — **404 unless** UI enabled |
| GET | `/oauth/callback` | OAuth callback — **404 unless** UI enabled |
| GET | `/oauth/token` | One-time token fetch by state (+ state cookie) — **404 unless** UI enabled |
| GET | `/oauth/info` | Redirect URI helper — **404 unless** UI enabled |
| POST | `/mcp/` | Streamable HTTP MCP |

## MCP tools

All tools accept `credentials_path` and/or `credentials_json` (**at least one** required).

Shared error shape when `success=false`:

```json
{
  "error_code": "CREDENTIALS_REQUIRED",
  "error_message": "…",
  "retryable": false,
  "original_provider_error": null
}
```

Common codes: `CREDENTIALS_REQUIRED`, `VALIDATION_ERROR`, `AUTH_ERROR`, `NOT_FOUND`, `PERMISSION_DENIED`, `RATE_LIMIT`, `PROVIDER_ERROR`, `UNKNOWN_ERROR`.

### Messages

| Tool | Key args |
|------|----------|
| `list_messages` | `q`, `label_ids` (CSV), `max_results`, `page_token`, `include_spam_trash`. Returns ids/`thread_id` only (`snippet` is null — use `get_message`). |
| `get_message` | `message_id`, `format` |
| `send_message` | `to`, `subject`, `body_text`/`body_html`, `cc`/`bcc`, `attachments` (JSON), `thread_id`, … |
| `reply_message` | `message_id`, body fields, `reply_all` (best-effort; does not exclude self) |
| `forward_message` | `message_id`, `to`, … — **text-oriented**; does not re-attach original attachments |
| `trash_message` / `untrash_message` / `delete_message` | `message_id` |
| `mark_message_read` / `mark_message_unread` | `message_id` |
| `modify_message_labels` | `message_id`, `add_label_ids`, `remove_label_ids` (CSV) |

### Threads / Drafts / Labels / Attachments

See README tools table. Labels CSV fields are comma-separated ids. Attachments JSON: `[{"filename","content_base64","mime_type"}]`.

## Failure matrix

| Problem | Channel |
|---------|---------|
| Missing credentials | Tool `success=false` `CREDENTIALS_REQUIRED` |
| Bad attachment JSON/size | `VALIDATION_ERROR` |
| Google 401/403/404/429 | Mapped GmailError codes |
| MCP protocol | FastMCP / JSON-RPC (framework) |
