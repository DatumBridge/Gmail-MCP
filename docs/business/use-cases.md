# Use Cases

| Use case | Tools |
|----------|-------|
| Inbox triage | `list_messages`, `get_message`, `modify_message_labels` |
| Send notification | `send_message` |
| Thread follow-up | `get_thread`, `reply_message` |
| Draft review | `create_draft`, `update_draft`, `send_draft` |
| Label automation | `list_labels`, `create_label`, `modify_message_labels` |
| Save attachment | `download_attachment` |

Deep Agent must follow `registry_docs/<tool>.md` for argument samples and `error_code` handling.

Not for: edge device mail, IMAP clients, or policy approval gates.
