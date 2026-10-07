# create_label

Create a new Gmail label.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `name` | yes | Label name |
| `message_list_visibility` | no | Message list visibility: show or hide |
| `label_list_visibility` | no | Label list visibility: labelShow, labelShowIfUnread, or labelHide |

## Cases

### Typical call

Input:

```json
{
  "name": "example-name"
}
```

Output:

```json
{
  "success": true,
  "label": "example",
  "message": "example"
}
```

### Missing `name`

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
    "error_message": "name is required",
    "retryable": false
  }
}
```
