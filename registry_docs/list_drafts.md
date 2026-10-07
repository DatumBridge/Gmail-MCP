# list_drafts

List Gmail drafts.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `max_results` | no | Maximum drafts to return (1-500) |
| `page_token` | no | Page token from a previous list_drafts response |
| `q` | no | Optional Gmail query to filter drafts |

## Cases

### Typical call

Input:

```json
{}
```

Output:

```json
{
  "success": true,
  "drafts": [],
  "next_page_token": "example"
}
```
