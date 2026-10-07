# get_message

Get a single Gmail message by ID.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `message_id` | yes | Gmail message ID |
| `format` | no | Message format: full, metadata, minimal, or raw |

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
  "message": "example"
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
