# forward_message

Forward an existing Gmail message.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `message_id` | yes | ID of the message to forward |
| `to` | yes | Forward recipient email address(es) |
| `body_text` | no | Optional note to prepend before the forwarded content |
| `body_html` | no | Optional HTML body |
| `cc` | no | CC recipients |
| `bcc` | no | BCC recipients |
| `include_original` | no | Include original message content in the forward |

## Cases

### Typical call

Input:

```json
{
  "message_id": "example-message-id",
  "to": "user@example.com",
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
  "to": "user@example.com",
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
