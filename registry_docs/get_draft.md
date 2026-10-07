# get_draft

Get a Gmail draft by ID.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `draft_id` | yes | Gmail draft ID |
| `format` | no | Draft message format: full, metadata, or minimal |

## Cases

### Typical call

Input:

```json
{
  "draft_id": "example-id"
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

### Missing `draft_id`

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
    "error_message": "draft_id is required",
    "retryable": false
  }
}
```
