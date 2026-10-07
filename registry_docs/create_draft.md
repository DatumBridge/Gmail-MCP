# create_draft

Create a new Gmail draft.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `to` | no | Recipient email address(es) |
| `subject` | no | Draft subject |
| `body_text` | no | Plain-text body |
| `body_html` | no | HTML body |
| `cc` | no | CC recipients |
| `bcc` | no | BCC recipients |
| `attachments` | no | Attachments as a JSON array string or array of objects [{"filename","content_base64","mime_type"}]. Empty list / empty string / omitted means no attachments. |
| `thread_id` | no | Optional thread ID for the draft |

## Cases

### Typical call

Input:

```json
{
  "body_text": "Hello from Weaver"
}
```

Output:

```json
{
  "success": true,
  "draft": "example",
  "draft_id": "example-id",
  "message_id": "example-message-id",
  "thread_id": "example-thread-id"
}
```
