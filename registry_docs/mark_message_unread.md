# mark_message_unread

Mark a message as unread (add UNREAD label).

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `message_id` | yes | Gmail message ID to mark as unread |

## Cases

### Typical call

Input:

```json
{
  "message_id": "example-message-id"
}
```

Output:

```json
{
  "success": true,
  "message_id": "example-message-id",
  "thread_id": "example-thread-id",
  "message": "example",
  "label_ids": []
}
```

### Missing `message_id`

The tool rejects the call and does not guess the missing value.

Input:

```json
{}
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
