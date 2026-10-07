# delete_label

Delete a Gmail label.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `label_id` | yes | Gmail label ID to delete |

## Cases

### Typical call

Input:

```json
{
  "label_id": "example-id"
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

### Missing `label_id`

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
    "error_message": "label_id is required",
    "retryable": false
  }
}
```
