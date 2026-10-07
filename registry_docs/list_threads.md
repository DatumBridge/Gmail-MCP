# list_threads

List Gmail threads matching optional query and labels.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `q` | no | Gmail search query |
| `label_ids` | no | Comma-separated label IDs to filter |
| `max_results` | no | Maximum threads to return (1-500) |
| `page_token` | no | Page token from a previous list_threads response |
| `include_spam_trash` | no | Include SPAM and TRASH in results |

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
  "threads": [],
  "result_size_estimate": "example",
  "next_page_token": "example"
}
```
