"""
Gmail MCP Server

Exposes Gmail capabilities via Model Context Protocol (MCP).
Uses fastmcp for MCP server implementation.

Tools: messages, threads, drafts, labels, attachments

Usage:
    # Run as standalone server (stdio mode for Claude Desktop):
    python -m app.mcp_server

    # Or with uvicorn for HTTP/SSE mode:
    uvicorn app.mcp_server:http_app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from fastmcp import FastMCP
from pydantic import Field

logger = logging.getLogger(__name__)

from app.schemas.mcp_models import (
    ActionResponse,
    AttachmentResponse,
    DraftListResponse,
    DraftResponse,
    LabelListResponse,
    LabelResponse,
    MessageListResponse,
    MessageResponse,
    SendMessageResponse,
    ThreadListResponse,
    ThreadResponse,
)
from app.services.gmail_service import GmailService
from app.core.exceptions import GmailError

# Initialize MCP Server
mcp = FastMCP(
    name="gmail",
    instructions="""
    Gmail MCP Server provides tools for:
    - Listing, reading, sending, replying, and forwarding messages
    - Trashing, restoring, deleting, and labeling messages
    - Listing and managing threads
    - Creating, updating, sending, and deleting drafts
    - Listing, creating, updating, and deleting labels
    - Downloading message attachments

    Use these tools to manage Gmail as part of workflows.
    Credentials must be passed as input: credentials_path or credentials_json.
    Note: permanent delete may require a broader OAuth scope than gmail.modify.
    """,
)


def _get_gmail_service(
    credentials_path: Optional[str] = None,
    credentials_json: Optional[str] = None,
) -> GmailService:
    """Create GmailService with credentials from tool input."""
    if not credentials_path and not credentials_json:
        raise GmailError(
            "Credentials required: provide credentials_path or credentials_json",
            error_code="CREDENTIALS_REQUIRED",
            retryable=False,
        )
    return GmailService(
        credentials_path=credentials_path,
        credentials_json=credentials_json,
    )


def _error_response(error: GmailError) -> dict:
    """Build error dict for response models."""
    return error.to_dict()


def _creds_required_error() -> dict:
    """Error dict when neither credentials_path nor credentials_json is provided."""
    return {
        "error_code": "CREDENTIALS_REQUIRED",
        "error_message": "Provide credentials_path or credentials_json",
        "retryable": False,
        "original_provider_error": None,
    }


def _parse_label_ids(label_ids: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated label IDs into a list, or None if empty."""
    if not label_ids or not str(label_ids).strip():
        return None
    parts = [p.strip() for p in str(label_ids).split(",")]
    result = [p for p in parts if p]
    return result or None


def _coerce_attachments_arg(value: Any) -> Optional[str]:
    """
    Accept planner-shaped attachments before/without strict string validation.

    LLMs often emit attachments as [] or a JSON array object. Empty → omit;
    non-empty list → JSON string for _parse_attachments.
    """
    if value is None:
        return None
    if isinstance(value, list):
        if len(value) == 0:
            return None
        try:
            return json.dumps(value)
        except (TypeError, ValueError):
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s or s in ("[]", "null", "None"):
            return None
        return value
    return None


def _parse_attachments(
    attachments: Any,
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[dict]]:
    """
    Parse attachments from a JSON string or already-decoded list.

    Expected: array of {filename, content_base64, mime_type}.
    Returns (parsed_list, None) on success, or (None, error_dict) on validation/JSON error.
    Empty / omitted attachments → (None, None).
    """
    if attachments is None:
        return None, None
    if isinstance(attachments, list):
        if len(attachments) == 0:
            return None, None
        parsed = attachments
    elif isinstance(attachments, str):
        s = attachments.strip()
        if not s or s in ("[]", "null", "None"):
            return None, None
        try:
            parsed = json.loads(attachments)
        except json.JSONDecodeError as e:
            return None, {
                "error_code": "VALIDATION_ERROR",
                "error_message": f"Invalid attachments JSON: {e}",
                "retryable": False,
                "original_provider_error": None,
            }
    else:
        # Coerce other shapes via the shared helper (e.g. unexpected types → omit).
        coerced = _coerce_attachments_arg(attachments)
        return _parse_attachments(coerced)

    if not isinstance(parsed, list):
        return None, {
            "error_code": "VALIDATION_ERROR",
            "error_message": "attachments must be a JSON array of "
            "{filename, content_base64, mime_type}",
            "retryable": False,
            "original_provider_error": None,
        }
    if len(parsed) == 0:
        return None, None
    return parsed, None


_CREDS_PATH_FIELD = Field(
    default=None,
    description=(
        "Path to OAuth token JSON file (e.g. token.json from oauth_connect.py). "
        "One of credentials_path or credentials_json required."
    ),
)
_CREDS_JSON_FIELD = Field(
    default=None,
    description=(
        "OAuth token JSON string. One of credentials_path or credentials_json required."
    ),
)


# ============== Message Tools ==============


@mcp.tool()
def list_messages(
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
    q: Optional[str] = Field(
        default=None,
        description="Gmail search query (e.g. from:user@example.com is:unread)",
    ),
    label_ids: Optional[str] = Field(
        default=None,
        description="Comma-separated label IDs to filter (e.g. INBOX,UNREAD)",
    ),
    max_results: int = Field(
        default=25,
        description="Maximum messages to return (1-500)",
    ),
    page_token: Optional[str] = Field(
        default=None,
        description="Page token from a previous list_messages response",
    ),
    include_spam_trash: bool = Field(
        default=False,
        description="Include SPAM and TRASH in results",
    ),
) -> MessageListResponse:
    """List Gmail messages matching optional query and labels."""
    logger.info("MCP: list_messages max_results=%s", max_results)
    try:
        if not credentials_path and not credentials_json:
            return MessageListResponse(
                success=False,
                messages=[],
                error=_creds_required_error(),
            )
        service = _get_gmail_service(credentials_path, credentials_json)
        messages, next_token, estimate = service.list_messages(
            q=q,
            label_ids=_parse_label_ids(label_ids),
            max_results=max_results,
            page_token=page_token,
            include_spam_trash=include_spam_trash,
        )
        return MessageListResponse(
            success=True,
            messages=messages,
            result_size_estimate=estimate,
            next_page_token=next_token,
        )
    except GmailError as e:
        logger.error("list_messages failed: %s", e.message)
        return MessageListResponse(
            success=False,
            messages=[],
            error=_error_response(e),
        )


@mcp.tool()
def get_message(
    message_id: str = Field(..., description="Gmail message ID"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
    format: str = Field(
        default="full",
        description="Message format: full, metadata, minimal, or raw",
    ),
) -> MessageResponse:
    """Get a single Gmail message by ID."""
    logger.info("MCP: get_message message_id=%s", message_id)
    try:
        if not credentials_path and not credentials_json:
            return MessageResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        message = service.get_message(message_id=message_id, format=format)
        return MessageResponse(success=True, message=message)
    except GmailError as e:
        logger.error("get_message failed: %s", e.message)
        return MessageResponse(success=False, error=_error_response(e))


@mcp.tool()
def send_message(
    to: str = Field(..., description="Recipient email address(es)"),
    subject: str = Field(..., description="Email subject"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
    body_text: Optional[str] = Field(
        default=None,
        description="Plain-text body",
    ),
    body_html: Optional[str] = Field(
        default=None,
        description="HTML body",
    ),
    cc: Optional[str] = Field(default=None, description="CC recipients"),
    bcc: Optional[str] = Field(default=None, description="BCC recipients"),
    attachments: Any = Field(
        default=None,
        description=(
            "Attachments as a JSON array string or array of objects "
            '[{"filename","content_base64","mime_type"}]. '
            "Empty list / empty string / omitted means no attachments."
        ),
    ),
    thread_id: Optional[str] = Field(
        default=None,
        description="Optional thread ID to send into an existing thread",
    ),
    in_reply_to: Optional[str] = Field(
        default=None,
        description="In-Reply-To header value (Message-ID)",
    ),
    references: Optional[str] = Field(
        default=None,
        description="References header value for threading",
    ),
) -> SendMessageResponse:
    """Send a new Gmail message."""
    logger.info("MCP: send_message to=%s", to)
    try:
        if not credentials_path and not credentials_json:
            return SendMessageResponse(success=False, error=_creds_required_error())
        parsed_attachments, att_error = _parse_attachments(attachments)
        if att_error:
            return SendMessageResponse(success=False, error=att_error)
        service = _get_gmail_service(credentials_path, credentials_json)
        result = service.send_message(
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            attachments=parsed_attachments,
            thread_id=thread_id,
            in_reply_to=in_reply_to,
            references=references,
        )
        return SendMessageResponse(
            success=True,
            message_id=result.get("id"),
            thread_id=result.get("thread_id"),
            label_ids=result.get("label_ids") or [],
        )
    except GmailError as e:
        logger.error("send_message failed: %s", e.message)
        return SendMessageResponse(success=False, error=_error_response(e))


@mcp.tool()
def reply_message(
    message_id: str = Field(..., description="ID of the message to reply to"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
    body_text: Optional[str] = Field(default=None, description="Plain-text reply body"),
    body_html: Optional[str] = Field(default=None, description="HTML reply body"),
    reply_all: bool = Field(
        default=False,
        description="If true, reply to all original recipients",
    ),
    attachments: Any = Field(
        default=None,
        description=(
            "Attachments as a JSON array string or array of objects "
            '[{"filename","content_base64","mime_type"}]. '
            "Empty list / empty string / omitted means no attachments."
        ),
    ),
) -> SendMessageResponse:
    """Reply to an existing Gmail message."""
    logger.info("MCP: reply_message message_id=%s", message_id)
    try:
        if not credentials_path and not credentials_json:
            return SendMessageResponse(success=False, error=_creds_required_error())
        parsed_attachments, att_error = _parse_attachments(attachments)
        if att_error:
            return SendMessageResponse(success=False, error=att_error)
        service = _get_gmail_service(credentials_path, credentials_json)
        result = service.reply_message(
            message_id=message_id,
            body_text=body_text,
            body_html=body_html,
            reply_all=reply_all,
            attachments=parsed_attachments,
        )
        return SendMessageResponse(
            success=True,
            message_id=result.get("id"),
            thread_id=result.get("thread_id"),
            label_ids=result.get("label_ids") or [],
        )
    except GmailError as e:
        logger.error("reply_message failed: %s", e.message)
        return SendMessageResponse(success=False, error=_error_response(e))


@mcp.tool()
def forward_message(
    message_id: str = Field(..., description="ID of the message to forward"),
    to: str = Field(..., description="Forward recipient email address(es)"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
    body_text: Optional[str] = Field(
        default=None,
        description="Optional note to prepend before the forwarded content",
    ),
    body_html: Optional[str] = Field(default=None, description="Optional HTML body"),
    cc: Optional[str] = Field(default=None, description="CC recipients"),
    bcc: Optional[str] = Field(default=None, description="BCC recipients"),
    include_original: bool = Field(
        default=True,
        description="Include original message content in the forward",
    ),
) -> SendMessageResponse:
    """Forward an existing Gmail message."""
    logger.info("MCP: forward_message message_id=%s to=%s", message_id, to)
    try:
        if not credentials_path and not credentials_json:
            return SendMessageResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        result = service.forward_message(
            message_id=message_id,
            to=to,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            include_original=include_original,
        )
        return SendMessageResponse(
            success=True,
            message_id=result.get("id"),
            thread_id=result.get("thread_id"),
            label_ids=result.get("label_ids") or [],
        )
    except GmailError as e:
        logger.error("forward_message failed: %s", e.message)
        return SendMessageResponse(success=False, error=_error_response(e))


@mcp.tool()
def trash_message(
    message_id: str = Field(..., description="Gmail message ID to trash"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
) -> ActionResponse:
    """Move a message to Trash."""
    logger.info("MCP: trash_message message_id=%s", message_id)
    try:
        if not credentials_path and not credentials_json:
            return ActionResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        result = service.trash_message(message_id=message_id)
        return ActionResponse(
            success=True,
            message_id=result.get("id"),
            thread_id=result.get("thread_id"),
            label_ids=result.get("label_ids") or [],
            message="Message moved to trash",
        )
    except GmailError as e:
        logger.error("trash_message failed: %s", e.message)
        return ActionResponse(success=False, error=_error_response(e))


@mcp.tool()
def untrash_message(
    message_id: str = Field(..., description="Gmail message ID to restore from trash"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
) -> ActionResponse:
    """Restore a message from Trash."""
    logger.info("MCP: untrash_message message_id=%s", message_id)
    try:
        if not credentials_path and not credentials_json:
            return ActionResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        result = service.untrash_message(message_id=message_id)
        return ActionResponse(
            success=True,
            message_id=result.get("id"),
            thread_id=result.get("thread_id"),
            label_ids=result.get("label_ids") or [],
            message="Message restored from trash",
        )
    except GmailError as e:
        logger.error("untrash_message failed: %s", e.message)
        return ActionResponse(success=False, error=_error_response(e))


@mcp.tool()
def delete_message(
    message_id: str = Field(..., description="Gmail message ID to permanently delete"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
) -> ActionResponse:
    """
    Permanently delete a message.
    Note: permanent delete may require a broader OAuth scope than gmail.modify
    (e.g. https://mail.google.com/).
    """
    logger.info("MCP: delete_message message_id=%s", message_id)
    try:
        if not credentials_path and not credentials_json:
            return ActionResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        service.delete_message(message_id=message_id)
        return ActionResponse(
            success=True,
            message_id=message_id,
            message="Message permanently deleted",
        )
    except GmailError as e:
        logger.error("delete_message failed: %s", e.message)
        return ActionResponse(success=False, error=_error_response(e))


@mcp.tool()
def mark_message_read(
    message_id: str = Field(..., description="Gmail message ID to mark as read"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
) -> ActionResponse:
    """Mark a message as read (remove UNREAD label)."""
    logger.info("MCP: mark_message_read message_id=%s", message_id)
    try:
        if not credentials_path and not credentials_json:
            return ActionResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        result = service.mark_message_read(message_id=message_id)
        return ActionResponse(
            success=True,
            message_id=result.get("id"),
            thread_id=result.get("thread_id"),
            label_ids=result.get("label_ids") or [],
            message="Message marked as read",
        )
    except GmailError as e:
        logger.error("mark_message_read failed: %s", e.message)
        return ActionResponse(success=False, error=_error_response(e))


@mcp.tool()
def mark_message_unread(
    message_id: str = Field(..., description="Gmail message ID to mark as unread"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
) -> ActionResponse:
    """Mark a message as unread (add UNREAD label)."""
    logger.info("MCP: mark_message_unread message_id=%s", message_id)
    try:
        if not credentials_path and not credentials_json:
            return ActionResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        result = service.mark_message_unread(message_id=message_id)
        return ActionResponse(
            success=True,
            message_id=result.get("id"),
            thread_id=result.get("thread_id"),
            label_ids=result.get("label_ids") or [],
            message="Message marked as unread",
        )
    except GmailError as e:
        logger.error("mark_message_unread failed: %s", e.message)
        return ActionResponse(success=False, error=_error_response(e))


@mcp.tool()
def modify_message_labels(
    message_id: str = Field(..., description="Gmail message ID"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
    add_label_ids: Optional[str] = Field(
        default=None,
        description="Comma-separated label IDs to add",
    ),
    remove_label_ids: Optional[str] = Field(
        default=None,
        description="Comma-separated label IDs to remove",
    ),
) -> ActionResponse:
    """Add and/or remove labels on a message."""
    logger.info("MCP: modify_message_labels message_id=%s", message_id)
    try:
        if not credentials_path and not credentials_json:
            return ActionResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        result = service.modify_message(
            message_id=message_id,
            add_label_ids=_parse_label_ids(add_label_ids),
            remove_label_ids=_parse_label_ids(remove_label_ids),
        )
        return ActionResponse(
            success=True,
            message_id=result.get("id"),
            thread_id=result.get("thread_id"),
            label_ids=result.get("label_ids") or [],
            message="Message labels updated",
        )
    except GmailError as e:
        logger.error("modify_message_labels failed: %s", e.message)
        return ActionResponse(success=False, error=_error_response(e))


# ============== Thread Tools ==============


@mcp.tool()
def list_threads(
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
    q: Optional[str] = Field(
        default=None,
        description="Gmail search query",
    ),
    label_ids: Optional[str] = Field(
        default=None,
        description="Comma-separated label IDs to filter",
    ),
    max_results: int = Field(
        default=25,
        description="Maximum threads to return (1-500)",
    ),
    page_token: Optional[str] = Field(
        default=None,
        description="Page token from a previous list_threads response",
    ),
    include_spam_trash: bool = Field(
        default=False,
        description="Include SPAM and TRASH in results",
    ),
) -> ThreadListResponse:
    """List Gmail threads matching optional query and labels."""
    logger.info("MCP: list_threads max_results=%s", max_results)
    try:
        if not credentials_path and not credentials_json:
            return ThreadListResponse(
                success=False,
                threads=[],
                error=_creds_required_error(),
            )
        service = _get_gmail_service(credentials_path, credentials_json)
        threads, next_token, estimate = service.list_threads(
            q=q,
            label_ids=_parse_label_ids(label_ids),
            max_results=max_results,
            page_token=page_token,
            include_spam_trash=include_spam_trash,
        )
        return ThreadListResponse(
            success=True,
            threads=threads,
            result_size_estimate=estimate,
            next_page_token=next_token,
        )
    except GmailError as e:
        logger.error("list_threads failed: %s", e.message)
        return ThreadListResponse(
            success=False,
            threads=[],
            error=_error_response(e),
        )


@mcp.tool()
def get_thread(
    thread_id: str = Field(..., description="Gmail thread ID"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
    format: str = Field(
        default="full",
        description="Message format within the thread: full, metadata, or minimal",
    ),
) -> ThreadResponse:
    """Get a Gmail thread with its messages."""
    logger.info("MCP: get_thread thread_id=%s", thread_id)
    try:
        if not credentials_path and not credentials_json:
            return ThreadResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        thread = service.get_thread(thread_id=thread_id, format=format)
        return ThreadResponse(success=True, thread=thread)
    except GmailError as e:
        logger.error("get_thread failed: %s", e.message)
        return ThreadResponse(success=False, error=_error_response(e))


@mcp.tool()
def trash_thread(
    thread_id: str = Field(..., description="Gmail thread ID to trash"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
) -> ActionResponse:
    """Move a thread to Trash."""
    logger.info("MCP: trash_thread thread_id=%s", thread_id)
    try:
        if not credentials_path and not credentials_json:
            return ActionResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        result = service.trash_thread(thread_id=thread_id)
        return ActionResponse(
            success=True,
            thread_id=result.get("id"),
            message="Thread moved to trash",
        )
    except GmailError as e:
        logger.error("trash_thread failed: %s", e.message)
        return ActionResponse(success=False, error=_error_response(e))


@mcp.tool()
def untrash_thread(
    thread_id: str = Field(..., description="Gmail thread ID to restore from trash"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
) -> ActionResponse:
    """Restore a thread from Trash."""
    logger.info("MCP: untrash_thread thread_id=%s", thread_id)
    try:
        if not credentials_path and not credentials_json:
            return ActionResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        result = service.untrash_thread(thread_id=thread_id)
        return ActionResponse(
            success=True,
            thread_id=result.get("id"),
            message="Thread restored from trash",
        )
    except GmailError as e:
        logger.error("untrash_thread failed: %s", e.message)
        return ActionResponse(success=False, error=_error_response(e))


@mcp.tool()
def delete_thread(
    thread_id: str = Field(..., description="Gmail thread ID to permanently delete"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
) -> ActionResponse:
    """
    Permanently delete a thread.
    Note: permanent delete may require a broader OAuth scope than gmail.modify.
    """
    logger.info("MCP: delete_thread thread_id=%s", thread_id)
    try:
        if not credentials_path and not credentials_json:
            return ActionResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        service.delete_thread(thread_id=thread_id)
        return ActionResponse(
            success=True,
            thread_id=thread_id,
            message="Thread permanently deleted",
        )
    except GmailError as e:
        logger.error("delete_thread failed: %s", e.message)
        return ActionResponse(success=False, error=_error_response(e))


@mcp.tool()
def modify_thread_labels(
    thread_id: str = Field(..., description="Gmail thread ID"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
    add_label_ids: Optional[str] = Field(
        default=None,
        description="Comma-separated label IDs to add",
    ),
    remove_label_ids: Optional[str] = Field(
        default=None,
        description="Comma-separated label IDs to remove",
    ),
) -> ActionResponse:
    """Add and/or remove labels on a thread."""
    logger.info("MCP: modify_thread_labels thread_id=%s", thread_id)
    try:
        if not credentials_path and not credentials_json:
            return ActionResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        result = service.modify_thread(
            thread_id=thread_id,
            add_label_ids=_parse_label_ids(add_label_ids),
            remove_label_ids=_parse_label_ids(remove_label_ids),
        )
        return ActionResponse(
            success=True,
            thread_id=result.get("id"),
            message="Thread labels updated",
        )
    except GmailError as e:
        logger.error("modify_thread_labels failed: %s", e.message)
        return ActionResponse(success=False, error=_error_response(e))


# ============== Draft Tools ==============


@mcp.tool()
def list_drafts(
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
    max_results: int = Field(
        default=25,
        description="Maximum drafts to return (1-500)",
    ),
    page_token: Optional[str] = Field(
        default=None,
        description="Page token from a previous list_drafts response",
    ),
    q: Optional[str] = Field(
        default=None,
        description="Optional Gmail query to filter drafts",
    ),
) -> DraftListResponse:
    """List Gmail drafts."""
    logger.info("MCP: list_drafts max_results=%s", max_results)
    try:
        if not credentials_path and not credentials_json:
            return DraftListResponse(
                success=False,
                drafts=[],
                error=_creds_required_error(),
            )
        service = _get_gmail_service(credentials_path, credentials_json)
        drafts, next_token = service.list_drafts(
            max_results=max_results,
            page_token=page_token,
            q=q,
        )
        return DraftListResponse(
            success=True,
            drafts=drafts,
            next_page_token=next_token,
        )
    except GmailError as e:
        logger.error("list_drafts failed: %s", e.message)
        return DraftListResponse(
            success=False,
            drafts=[],
            error=_error_response(e),
        )


@mcp.tool()
def get_draft(
    draft_id: str = Field(..., description="Gmail draft ID"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
    format: str = Field(
        default="full",
        description="Draft message format: full, metadata, or minimal",
    ),
) -> DraftResponse:
    """Get a Gmail draft by ID."""
    logger.info("MCP: get_draft draft_id=%s", draft_id)
    try:
        if not credentials_path and not credentials_json:
            return DraftResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        draft = service.get_draft(draft_id=draft_id, format=format)
        return DraftResponse(
            success=True,
            draft=draft,
            draft_id=draft.get("id"),
            message_id=(draft.get("message") or {}).get("id")
            if isinstance(draft.get("message"), dict)
            else None,
            thread_id=(draft.get("message") or {}).get("thread_id")
            if isinstance(draft.get("message"), dict)
            else None,
        )
    except GmailError as e:
        logger.error("get_draft failed: %s", e.message)
        return DraftResponse(success=False, error=_error_response(e))


@mcp.tool()
def create_draft(
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
    to: Optional[str] = Field(default=None, description="Recipient email address(es)"),
    subject: Optional[str] = Field(default=None, description="Draft subject"),
    body_text: Optional[str] = Field(default=None, description="Plain-text body"),
    body_html: Optional[str] = Field(default=None, description="HTML body"),
    cc: Optional[str] = Field(default=None, description="CC recipients"),
    bcc: Optional[str] = Field(default=None, description="BCC recipients"),
    attachments: Any = Field(
        default=None,
        description=(
            "Attachments as a JSON array string or array of objects "
            '[{"filename","content_base64","mime_type"}]. '
            "Empty list / empty string / omitted means no attachments."
        ),
    ),
    thread_id: Optional[str] = Field(
        default=None,
        description="Optional thread ID for the draft",
    ),
) -> DraftResponse:
    """Create a new Gmail draft."""
    logger.info("MCP: create_draft")
    try:
        if not credentials_path and not credentials_json:
            return DraftResponse(success=False, error=_creds_required_error())
        parsed_attachments, att_error = _parse_attachments(attachments)
        if att_error:
            return DraftResponse(success=False, error=att_error)
        service = _get_gmail_service(credentials_path, credentials_json)
        result = service.create_draft(
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            attachments=parsed_attachments,
            thread_id=thread_id,
        )
        return DraftResponse(
            success=True,
            draft=result,
            draft_id=result.get("id"),
            message_id=result.get("message_id"),
            thread_id=result.get("thread_id"),
        )
    except GmailError as e:
        logger.error("create_draft failed: %s", e.message)
        return DraftResponse(success=False, error=_error_response(e))


@mcp.tool()
def update_draft(
    draft_id: str = Field(..., description="Gmail draft ID to update"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
    to: Optional[str] = Field(default=None, description="Recipient email address(es)"),
    subject: Optional[str] = Field(default=None, description="Draft subject"),
    body_text: Optional[str] = Field(default=None, description="Plain-text body"),
    body_html: Optional[str] = Field(default=None, description="HTML body"),
    cc: Optional[str] = Field(default=None, description="CC recipients"),
    bcc: Optional[str] = Field(default=None, description="BCC recipients"),
    attachments: Any = Field(
        default=None,
        description=(
            "Attachments as a JSON array string or array of objects "
            '[{"filename","content_base64","mime_type"}]. '
            "Empty list / empty string / omitted means no attachments."
        ),
    ),
    thread_id: Optional[str] = Field(
        default=None,
        description="Optional thread ID for the draft",
    ),
) -> DraftResponse:
    """Update an existing Gmail draft."""
    logger.info("MCP: update_draft draft_id=%s", draft_id)
    try:
        if not credentials_path and not credentials_json:
            return DraftResponse(success=False, error=_creds_required_error())
        parsed_attachments, att_error = _parse_attachments(attachments)
        if att_error:
            return DraftResponse(success=False, error=att_error)
        service = _get_gmail_service(credentials_path, credentials_json)
        result = service.update_draft(
            draft_id=draft_id,
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            attachments=parsed_attachments,
            thread_id=thread_id,
        )
        return DraftResponse(
            success=True,
            draft=result,
            draft_id=result.get("id"),
            message_id=result.get("message_id"),
            thread_id=result.get("thread_id"),
        )
    except GmailError as e:
        logger.error("update_draft failed: %s", e.message)
        return DraftResponse(success=False, error=_error_response(e))


@mcp.tool()
def send_draft(
    draft_id: str = Field(..., description="Gmail draft ID to send"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
) -> SendMessageResponse:
    """Send an existing Gmail draft."""
    logger.info("MCP: send_draft draft_id=%s", draft_id)
    try:
        if not credentials_path and not credentials_json:
            return SendMessageResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        result = service.send_draft(draft_id=draft_id)
        return SendMessageResponse(
            success=True,
            message_id=result.get("id"),
            thread_id=result.get("thread_id"),
            label_ids=result.get("label_ids") or [],
        )
    except GmailError as e:
        logger.error("send_draft failed: %s", e.message)
        return SendMessageResponse(success=False, error=_error_response(e))


@mcp.tool()
def delete_draft(
    draft_id: str = Field(..., description="Gmail draft ID to delete"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
) -> ActionResponse:
    """Delete a Gmail draft."""
    logger.info("MCP: delete_draft draft_id=%s", draft_id)
    try:
        if not credentials_path and not credentials_json:
            return ActionResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        service.delete_draft(draft_id=draft_id)
        return ActionResponse(
            success=True,
            message=f"Draft {draft_id} deleted",
        )
    except GmailError as e:
        logger.error("delete_draft failed: %s", e.message)
        return ActionResponse(success=False, error=_error_response(e))


# ============== Label Tools ==============


@mcp.tool()
def list_labels(
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
) -> LabelListResponse:
    """List all Gmail labels."""
    logger.info("MCP: list_labels")
    try:
        if not credentials_path and not credentials_json:
            return LabelListResponse(
                success=False,
                labels=[],
                error=_creds_required_error(),
            )
        service = _get_gmail_service(credentials_path, credentials_json)
        labels = service.list_labels()
        return LabelListResponse(success=True, labels=labels)
    except GmailError as e:
        logger.error("list_labels failed: %s", e.message)
        return LabelListResponse(
            success=False,
            labels=[],
            error=_error_response(e),
        )


@mcp.tool()
def create_label(
    name: str = Field(..., description="Label name"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
    message_list_visibility: str = Field(
        default="show",
        description="Message list visibility: show or hide",
    ),
    label_list_visibility: str = Field(
        default="labelShow",
        description="Label list visibility: labelShow, labelShowIfUnread, or labelHide",
    ),
) -> LabelResponse:
    """Create a new Gmail label."""
    logger.info("MCP: create_label name=%s", name)
    try:
        if not credentials_path and not credentials_json:
            return LabelResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        label = service.create_label(
            name=name,
            message_list_visibility=message_list_visibility,
            label_list_visibility=label_list_visibility,
        )
        return LabelResponse(success=True, label=label, message="Label created")
    except GmailError as e:
        logger.error("create_label failed: %s", e.message)
        return LabelResponse(success=False, error=_error_response(e))


@mcp.tool()
def update_label(
    label_id: str = Field(..., description="Gmail label ID to update"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
    name: Optional[str] = Field(default=None, description="New label name"),
    message_list_visibility: Optional[str] = Field(
        default=None,
        description="Message list visibility: show or hide",
    ),
    label_list_visibility: Optional[str] = Field(
        default=None,
        description="Label list visibility: labelShow, labelShowIfUnread, or labelHide",
    ),
) -> LabelResponse:
    """Update an existing Gmail label."""
    logger.info("MCP: update_label label_id=%s", label_id)
    try:
        if not credentials_path and not credentials_json:
            return LabelResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        label = service.update_label(
            label_id=label_id,
            name=name,
            message_list_visibility=message_list_visibility,
            label_list_visibility=label_list_visibility,
        )
        return LabelResponse(success=True, label=label, message="Label updated")
    except GmailError as e:
        logger.error("update_label failed: %s", e.message)
        return LabelResponse(success=False, error=_error_response(e))


@mcp.tool()
def delete_label(
    label_id: str = Field(..., description="Gmail label ID to delete"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
) -> ActionResponse:
    """Delete a Gmail label."""
    logger.info("MCP: delete_label label_id=%s", label_id)
    try:
        if not credentials_path and not credentials_json:
            return ActionResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        service.delete_label(label_id=label_id)
        return ActionResponse(
            success=True,
            message=f"Label {label_id} deleted",
        )
    except GmailError as e:
        logger.error("delete_label failed: %s", e.message)
        return ActionResponse(success=False, error=_error_response(e))


# ============== Attachment Tools ==============


@mcp.tool()
def download_attachment(
    message_id: str = Field(..., description="Gmail message ID containing the attachment"),
    attachment_id: str = Field(..., description="Attachment ID within the message"),
    credentials_path: Optional[str] = _CREDS_PATH_FIELD,
    credentials_json: Optional[str] = _CREDS_JSON_FIELD,
) -> AttachmentResponse:
    """Download a message attachment as base64 content."""
    logger.info(
        "MCP: download_attachment message_id=%s attachment_id=%s",
        message_id,
        attachment_id,
    )
    try:
        if not credentials_path and not credentials_json:
            return AttachmentResponse(success=False, error=_creds_required_error())
        service = _get_gmail_service(credentials_path, credentials_json)
        result = service.download_attachment(
            message_id=message_id,
            attachment_id=attachment_id,
        )
        return AttachmentResponse(
            success=True,
            message_id=result.get("message_id"),
            attachment_id=result.get("attachment_id"),
            size=result.get("size"),
            content_base64=result.get("content_base64"),
        )
    except GmailError as e:
        logger.error("download_attachment failed: %s", e.message)
        return AttachmentResponse(success=False, error=_error_response(e))


# ============== HTTP App with Health Endpoint ==============

# Create ASGI app for HTTP/SSE transport
_base_app = mcp.http_app()

# Wrap to add /health and test UI - must pass MCP lifespan for Streamable HTTP session manager
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse, FileResponse

from app.oauth_routes import (
    oauth_start,
    oauth_callback,
    oauth_token,
    oauth_info,
    _oauth_ui_enabled,
)


async def health(request):
    return JSONResponse({"status": "ok", "service": "gmail-mcp"})


async def test_ui(request):
    """Serve the manual test UI for MCP tools (local-dev when OAuth UI enabled)."""
    if not _oauth_ui_enabled():
        return JSONResponse(
            {
                "error_code": "OAUTH_UI_DISABLED",
                "error_message": "Test UI disabled. Set GMAIL_ENABLE_OAUTH_UI=1 for local use.",
                "retryable": False,
            },
            status_code=404,
        )
    ui_path = Path(__file__).resolve().parent.parent / "static" / "test-ui.html"
    if not ui_path.exists():
        return JSONResponse({"error": "test-ui.html not found"}, status_code=404)
    return FileResponse(ui_path, media_type="text/html")


http_app = Starlette(
    routes=[
        Route("/health", health),
        Route("/test", test_ui),
        Route("/oauth/start", oauth_start),
        Route("/oauth/callback", oauth_callback),
        Route("/oauth/token", oauth_token),
        Route("/oauth/info", oauth_info),
        Mount("/", _base_app),
    ],
    lifespan=getattr(_base_app, "lifespan", None),
)


# ============== Main Entry Point ==============

if __name__ == "__main__":
    logger.info("Starting Gmail MCP Server (stdio mode)")
    mcp.run()
