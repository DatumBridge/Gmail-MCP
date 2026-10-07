# send_message

Send a new Gmail message.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `to` | yes | Recipient email address(es) |
| `subject` | yes | Email subject |
| `body_text` | no | Plain-text body |
| `body_html` | no | HTML body |
| `cc` | no | CC recipients |
| `bcc` | no | BCC recipients |
| `attachments` | no | Attachments as a JSON array string or array of objects [{"filename","content_base64","mime_type"}]. Empty list / empty string / omitted means no attachments. |
| `thread_id` | no | Optional thread ID to send into an existing thread |
| `in_reply_to` | no | In-Reply-To header value (Message-ID) |
| `references` | no | References header value for threading |

## Cases

### Typical call

Input:

```json
{
  "to": "user@example.com",
  "subject": "Status update",
  "body_text": "Hello from Weaver"
}
```

Output:

```json
{
  "success": true,
  "message_id": "example-message-id",
  "thread_id": "example-thread-id",
  "label_ids": []
}
```

### Missing `to`

The tool rejects the call and does not guess the missing value.

Input:

```json
{
  "subject": "Status update",
  "body_text": "Hello from Weaver"
}
```

Output:

```json
{
  "success": false,
  "error": {
    "error_code": "invalid_argument",
    "error_message": "to is required",
    "retryable": false
  }
}
```
