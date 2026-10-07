# list_messages

List Gmail messages matching optional query and labels.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `q` | no | Gmail search query (e.g. from:user@example.com is:unread) |
| `label_ids` | no | Comma-separated label IDs to filter (e.g. INBOX,UNREAD) |
| `max_results` | no | Maximum messages to return (1-500) |
| `page_token` | no | Page token from a previous list_messages response |
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
  "messages": [],
  "result_size_estimate": "example",
  "next_page_token": "example"
}
```
