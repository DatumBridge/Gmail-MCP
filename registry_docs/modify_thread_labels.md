# modify_thread_labels

Add and/or remove labels on a thread.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `thread_id` | yes | Gmail thread ID |
| `add_label_ids` | no | Comma-separated label IDs to add |
| `remove_label_ids` | no | Comma-separated label IDs to remove |

## Cases

### Typical call

Input:

```json
{
  "thread_id": "example-thread-id"
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

### Missing `thread_id`

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
    "error_message": "thread_id is required",
    "retryable": false
  }
}
```
