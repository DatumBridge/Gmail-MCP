# download_attachment

Download a message attachment as base64 content.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `message_id` | yes | Gmail message ID containing the attachment |
| `attachment_id` | yes | Attachment ID within the message |

## Cases

### Typical call

Input:

```json
{
  "message_id": "example-message-id",
  "attachment_id": "example-id"
}
```

Output:

```json
{
  "success": true,
  "message_id": "example-message-id",
  "attachment_id": "example-id",
  "filename": "notes.txt",
  "mime_type": "example",
  "size": "example",
  "content_base64": "example"
}
```

### Missing `message_id`

The tool rejects the call and does not guess the missing value.

Input:

```json
{
  "attachment_id": "example-id"
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
