# delete_thread

Permanently delete a thread. Note: permanent delete may require a broader OAuth scope than gmail.modify.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `thread_id` | yes | Gmail thread ID to permanently delete |

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
