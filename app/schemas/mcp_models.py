"""Pydantic models for Gmail MCP Server tools."""

from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict


class ErrorBody(BaseModel):
    error_code: str
    error_message: str
    retryable: bool = False
    original_provider_error: Optional[str] = None


class MessageSummary(BaseModel):
    id: str
    thread_id: Optional[str] = None
    snippet: Optional[str] = None
    label_ids: List[str] = Field(default_factory=list)
    history_id: Optional[str] = None
    internal_date: Optional[str] = None


class LabelInfo(BaseModel):
    id: str
    name: str
    type: Optional[str] = None
    message_list_visibility: Optional[str] = None
    label_list_visibility: Optional[str] = None


class DraftInfo(BaseModel):
    id: str
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    snippet: Optional[str] = None


class AttachmentInfo(BaseModel):
    attachment_id: str
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    size: Optional[int] = None


class BaseToolResponse(BaseModel):
    success: bool
    error: Optional[dict] = None


class MessageListResponse(BaseToolResponse):
    messages: List[MessageSummary] = Field(default_factory=list)
    result_size_estimate: Optional[int] = None
    next_page_token: Optional[str] = None


class MessageResponse(BaseToolResponse):
    message: Optional[Dict[str, Any]] = None


class ThreadListResponse(BaseToolResponse):
    threads: List[Dict[str, Any]] = Field(default_factory=list)
    result_size_estimate: Optional[int] = None
    next_page_token: Optional[str] = None


class ThreadResponse(BaseToolResponse):
    thread: Optional[Dict[str, Any]] = None


class SendMessageResponse(BaseToolResponse):
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    label_ids: List[str] = Field(default_factory=list)


class ActionResponse(BaseToolResponse):
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    message: Optional[str] = None
    label_ids: List[str] = Field(default_factory=list)


class LabelListResponse(BaseToolResponse):
    labels: List[LabelInfo] = Field(default_factory=list)


class LabelResponse(BaseToolResponse):
    label: Optional[LabelInfo] = None
    message: Optional[str] = None


class DraftListResponse(BaseToolResponse):
    drafts: List[DraftInfo] = Field(default_factory=list)
    next_page_token: Optional[str] = None


class DraftResponse(BaseToolResponse):
    draft: Optional[Dict[str, Any]] = None
    draft_id: Optional[str] = None
    message_id: Optional[str] = None
    thread_id: Optional[str] = None


class AttachmentResponse(BaseToolResponse):
    message_id: Optional[str] = None
    attachment_id: Optional[str] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    size: Optional[int] = None
    content_base64: Optional[str] = None
