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

All tools accept `credentials_path` and/or `credentials_json` (**at least one** required). In Studio, the gateway injects `credentials_json`; Deep Agent must omit both fields.

Deep Agent usage guides live in `registry_docs/<tool>.md` (parameter **Sample** column, success samples, error-code table, input/output cases). The server copies each file onto `tools/list` as `x-datumbridge-docs`. After deploy, run Tool Registry Setup or publish so the Docs field refreshes. Regenerate with `python3 scripts/generate_registry_docs.py`.

Shared error shape when `success=false`:

```json
{
  "success": false,
  "error": {
    "error_code": "CREDENTIALS_REQUIRED",
    "error_message": "…",
    "retryable": false,
    "original_provider_error": null
  }
}
```

| `error_code` | retryable | When |
|---|---|---|
| `CREDENTIALS_REQUIRED` | false | Neither `credentials_path` nor `credentials_json` after gateway inject |
| `INVALID_CREDENTIALS` | false | Token JSON is not valid OAuth |
| `VALIDATION_ERROR` | false | Bad args, attachment JSON/base64, empty label patch, oversize attachment |
| `NOT_FOUND` | false | Google 404 |
| `AUTH_ERROR` | true | Google 401 |
| `PERMISSION_DENIED` | false | Google 403 / missing scope |
| `RATE_LIMIT` | true | Google 429 / quota |
| `PROVIDER_ERROR` | true | Google 5xx |
| `UNKNOWN_ERROR` | false | Unmapped provider error |
| `GMAIL_ERROR` | false | Generic wrapper |

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
