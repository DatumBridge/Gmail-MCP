# reply_message

Reply to an existing Gmail message.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `message_id` | yes | ID of the message to reply to |
| `body_text` | no | Plain-text reply body |
| `body_html` | no | HTML reply body |
| `reply_all` | no | If true, reply to all original recipients |
| `attachments` | no | Attachments as a JSON array string or array of objects [{"filename","content_base64","mime_type"}]. Empty list / empty string / omitted means no attachments. |

## Cases

### Typical call

Input:

```json
{
  "message_id": "example-message-id",
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

### Missing `message_id`

The tool rejects the call and does not guess the missing value.

Input:

```json
{
  "body_text": "Hello from Weaver"
}
```

Output:

```json
{
  "success": false,
  "error": {
    "error_code": "invalid_argument",
    "error_message": "message_id is required",
    "retryable": false
  }
}
```
