# get_thread

Get a Gmail thread with its messages.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `thread_id` | yes | Gmail thread ID |
| `format` | no | Message format within the thread: full, metadata, or minimal |

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
  "thread": "example"
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
