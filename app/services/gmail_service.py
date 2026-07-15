"""
Gmail API wrapper layer.

All Google Gmail API logic lives here. Credentials are passed as input
(credentials_path or credentials_json) — not from environment defaults.
"""

from __future__ import annotations

import base64
import email.encoders
import email.mime.base
import email.mime.multipart
import email.mime.text
import json
import mimetypes
import os
from email.utils import formatdate, make_msgid
from typing import Any, Dict, List, Optional, Tuple

from google.oauth2.credentials import Credentials as OAuth2Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.exceptions import (
    GmailError,
    GmailValidationError,
    normalize_google_error,
)
from app.schemas.mcp_models import (
    AttachmentInfo,
    DraftInfo,
    LabelInfo,
    MessageSummary,
)

# gmail.modify covers read, send, drafts, labels, trash (not permanent delete).
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

DEFAULT_MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 25 MiB


def _max_attachment_bytes() -> int:
    raw = os.environ.get("GMAIL_MAX_ATTACHMENT_BYTES", "").strip()
    if not raw:
        return DEFAULT_MAX_ATTACHMENT_BYTES
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MAX_ATTACHMENT_BYTES


def _is_oauth_creds(creds_dict: dict) -> bool:
    return (
        creds_dict.get("type") == "oauth"
        or (creds_dict.get("refresh_token") and creds_dict.get("client_id"))
        or (creds_dict.get("refresh_token") and "client_secret" in creds_dict)
    )


def _get_credentials(
    credentials_path: Optional[str] = None,
    credentials_json: Optional[str] = None,
):
    creds_dict = None
    try:
        if credentials_json:
            creds_dict = json.loads(credentials_json)
        elif credentials_path and os.path.exists(credentials_path):
            with open(credentials_path) as f:
                creds_dict = json.load(f)
        elif credentials_path:
            raise GmailError(
                f"Credentials file not found: {credentials_path}",
                error_code="CREDENTIALS_REQUIRED",
                retryable=False,
            )
    except GmailError:
        raise
    except json.JSONDecodeError as e:
        raise GmailError(
            "Invalid credentials JSON",
            error_code="INVALID_CREDENTIALS",
            retryable=False,
            original_error=e,
        ) from e
    except OSError as e:
        raise GmailError(
            "Unable to read credentials file",
            error_code="INVALID_CREDENTIALS",
            retryable=False,
            original_error=e,
        ) from e

    if not creds_dict or not isinstance(creds_dict, dict):
        raise GmailError(
            "Credentials required: provide credentials_path or credentials_json (OAuth token)",
            error_code="CREDENTIALS_REQUIRED",
            retryable=False,
        )

    if not _is_oauth_creds(creds_dict):
        raise GmailError(
            "OAuth credentials required. Use Connect with Google in the test UI "
            "or run scripts/oauth_connect.py to get a token.",
            error_code="INVALID_CREDENTIALS",
            retryable=False,
        )

    return OAuth2Credentials(
        token=creds_dict.get("token") or creds_dict.get("access_token"),
        refresh_token=creds_dict.get("refresh_token"),
        token_uri=creds_dict.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=creds_dict.get("client_id"),
        client_secret=creds_dict.get("client_secret"),
        scopes=creds_dict.get("scopes", SCOPES),
    )


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _header_map(payload: dict) -> Dict[str, str]:
    headers = payload.get("headers") or []
    return {h.get("name", "").lower(): h.get("value", "") for h in headers}


def _decode_body_data(data: Optional[str]) -> str:
    if not data:
        return ""
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad).decode("utf-8", errors="replace")


def _collect_parts(
    payload: dict,
    bodies: Dict[str, str],
    attachments: List[AttachmentInfo],
) -> None:
    mime = payload.get("mimeType", "")
    filename = payload.get("filename") or None
    body = payload.get("body") or {}
    att_id = body.get("attachmentId")
    size = body.get("size")

    if filename and att_id:
        attachments.append(
            AttachmentInfo(
                attachment_id=att_id,
                filename=filename,
                mime_type=mime,
                size=size,
            )
        )
    elif mime == "text/plain" and body.get("data"):
        bodies["text"] = bodies.get("text", "") + _decode_body_data(body.get("data"))
    elif mime == "text/html" and body.get("data"):
        bodies["html"] = bodies.get("html", "") + _decode_body_data(body.get("data"))

    for part in payload.get("parts") or []:
        _collect_parts(part, bodies, attachments)


def _normalize_message(msg: dict, include_body: bool = True) -> Dict[str, Any]:
    payload = msg.get("payload") or {}
    headers = _header_map(payload)
    bodies: Dict[str, str] = {}
    attachments: List[AttachmentInfo] = []
    if include_body:
        _collect_parts(payload, bodies, attachments)
        if not bodies and payload.get("body", {}).get("data"):
            bodies["text"] = _decode_body_data(payload["body"]["data"])

    out: Dict[str, Any] = {
        "id": msg.get("id"),
        "thread_id": msg.get("threadId"),
        "snippet": msg.get("snippet"),
        "label_ids": msg.get("labelIds") or [],
        "history_id": msg.get("historyId"),
        "internal_date": msg.get("internalDate"),
        "size_estimate": msg.get("sizeEstimate"),
        "headers": {
            "from": headers.get("from"),
            "to": headers.get("to"),
            "cc": headers.get("cc"),
            "bcc": headers.get("bcc"),
            "subject": headers.get("subject"),
            "date": headers.get("date"),
            "message_id": headers.get("message-id"),
            "in_reply_to": headers.get("in-reply-to"),
            "references": headers.get("references"),
        },
    }
    if include_body:
        out["body_text"] = bodies.get("text")
        out["body_html"] = bodies.get("html")
        out["attachments"] = [a.model_dump() for a in attachments]
    return out


class GmailService:
    """Stateless Gmail API wrapper. Credentials passed at construction."""

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        credentials_json: Optional[str] = None,
    ):
        creds = _get_credentials(
            credentials_path=credentials_path,
            credentials_json=credentials_json,
        )
        self._service = build("gmail", "v1", credentials=creds)
        self._user = "me"

    @property
    def service(self):
        return self._service

    def _build_mime(
        self,
        *,
        to: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        subject: Optional[str] = None,
        body_text: Optional[str] = None,
        body_html: Optional[str] = None,
        attachments: Optional[List[Dict[str, str]]] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        attachments = attachments or []
        max_bytes = _max_attachment_bytes()

        if body_html and (attachments or body_text):
            root = email.mime.multipart.MIMEMultipart("mixed")
            alt = email.mime.multipart.MIMEMultipart("alternative")
            if body_text:
                alt.attach(email.mime.text.MIMEText(body_text, "plain", "utf-8"))
            alt.attach(email.mime.text.MIMEText(body_html, "html", "utf-8"))
            root.attach(alt)
            msg = root
        elif body_html:
            msg = email.mime.text.MIMEText(body_html, "html", "utf-8")
        elif attachments:
            msg = email.mime.multipart.MIMEMultipart()
            msg.attach(email.mime.text.MIMEText(body_text or "", "plain", "utf-8"))
        else:
            msg = email.mime.text.MIMEText(body_text or "", "plain", "utf-8")

        if to:
            msg["To"] = to
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc
        if subject is not None:
            msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references

        for att in attachments:
            filename = att.get("filename") or "attachment"
            content_b64 = att.get("content_base64") or ""
            mime_type = att.get("mime_type") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
            # Reject oversized base64 before decoding into memory (≈4/3 expansion).
            estimated = (len(content_b64) * 3) // 4
            if estimated > max_bytes:
                raise GmailValidationError(
                    f"Attachment {filename} exceeds GMAIL_MAX_ATTACHMENT_BYTES ({max_bytes})"
                )
            try:
                raw = base64.b64decode(content_b64, validate=False)
            except Exception as e:
                raise GmailValidationError(f"Invalid attachment base64 for {filename}") from e
            if len(raw) > max_bytes:
                raise GmailValidationError(
                    f"Attachment {filename} exceeds GMAIL_MAX_ATTACHMENT_BYTES ({max_bytes})"
                )
            maintype, _, subtype = mime_type.partition("/")
            if maintype == "text":
                part = email.mime.text.MIMEText(
                    raw.decode("utf-8", errors="replace"), _subtype=subtype or "plain", _charset="utf-8"
                )
            else:
                part = email.mime.base.MIMEBase(maintype or "application", subtype or "octet-stream")
                part.set_payload(raw)
                email.encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment", filename=filename)
            if not isinstance(msg, email.mime.multipart.MIMEMultipart):
                wrapper = email.mime.multipart.MIMEMultipart()
                wrapper.attach(msg)
                msg = wrapper
            msg.attach(part)

        raw = _b64url_encode(msg.as_bytes())
        return raw, thread_id

    # ---- Messages ----

    def list_messages(
        self,
        q: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
        max_results: int = 25,
        page_token: Optional[str] = None,
        include_spam_trash: bool = False,
    ) -> Tuple[List[MessageSummary], Optional[str], Optional[int]]:
        try:
            kwargs: Dict[str, Any] = {
                "userId": self._user,
                "maxResults": min(max(1, max_results), 500),
                "includeSpamTrash": include_spam_trash,
            }
            if q:
                kwargs["q"] = q
            if label_ids:
                kwargs["labelIds"] = label_ids
            if page_token:
                kwargs["pageToken"] = page_token
            result = self.service.users().messages().list(**kwargs).execute()
            # messages.list returns id/threadId only — use get_message for snippet/body.
            messages = [
                MessageSummary(
                    id=m["id"],
                    thread_id=m.get("threadId"),
                    snippet=None,
                )
                for m in result.get("messages") or []
            ]
            return messages, result.get("nextPageToken"), result.get("resultSizeEstimate")
        except HttpError as e:
            raise normalize_google_error(e) from e

    def get_message(
        self,
        message_id: str,
        format: str = "full",
    ) -> Dict[str, Any]:
        try:
            fmt = format if format in ("full", "metadata", "minimal", "raw") else "full"
            msg = (
                self.service.users()
                .messages()
                .get(userId=self._user, id=message_id, format=fmt)
                .execute()
            )
            if fmt == "raw":
                return {
                    "id": msg.get("id"),
                    "thread_id": msg.get("threadId"),
                    "raw": msg.get("raw"),
                    "label_ids": msg.get("labelIds") or [],
                    "snippet": msg.get("snippet"),
                }
            return _normalize_message(msg, include_body=fmt == "full")
        except HttpError as e:
            raise normalize_google_error(e) from e

    def send_message(
        self,
        to: str,
        subject: str,
        body_text: Optional[str] = None,
        body_html: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        attachments: Optional[List[Dict[str, str]]] = None,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            raw, tid = self._build_mime(
                to=to,
                cc=cc,
                bcc=bcc,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                attachments=attachments,
                in_reply_to=in_reply_to,
                references=references,
                thread_id=thread_id,
            )
            body: Dict[str, Any] = {"raw": raw}
            if tid:
                body["threadId"] = tid
            sent = self.service.users().messages().send(userId=self._user, body=body).execute()
            return {
                "id": sent.get("id"),
                "thread_id": sent.get("threadId"),
                "label_ids": sent.get("labelIds") or [],
            }
        except HttpError as e:
            raise normalize_google_error(e) from e
        except GmailError:
            raise

    def reply_message(
        self,
        message_id: str,
        body_text: Optional[str] = None,
        body_html: Optional[str] = None,
        reply_all: bool = False,
        attachments: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        original = self.get_message(message_id, format="full")
        headers = original.get("headers") or {}
        subject = headers.get("subject") or ""
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        to = headers.get("from") or ""
        cc = None
        if reply_all:
            # Keep original To/Cc excluding would-be self is best-effort; pass through To as From, Cc as Cc.
            parts = [p for p in [headers.get("to"), headers.get("cc")] if p]
            cc = ", ".join(parts) if parts else None
        msg_id_hdr = headers.get("message_id") or ""
        refs = headers.get("references") or ""
        if msg_id_hdr:
            references = f"{refs} {msg_id_hdr}".strip() if refs else msg_id_hdr
        else:
            references = refs or None
        return self.send_message(
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            attachments=attachments,
            thread_id=original.get("thread_id"),
            in_reply_to=msg_id_hdr or None,
            references=references,
        )

    def forward_message(
        self,
        message_id: str,
        to: str,
        body_text: Optional[str] = None,
        body_html: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        include_original: bool = True,
    ) -> Dict[str, Any]:
        original = self.get_message(message_id, format="full")
        headers = original.get("headers") or {}
        subject = headers.get("subject") or ""
        if not subject.lower().startswith("fwd:"):
            subject = f"Fwd: {subject}"
        fwd_text = body_text or ""
        if include_original:
            fwd_text = (
                f"{fwd_text}\n\n---------- Forwarded message ----------\n"
                f"From: {headers.get('from')}\n"
                f"Date: {headers.get('date')}\n"
                f"Subject: {headers.get('subject')}\n"
                f"To: {headers.get('to')}\n\n"
                f"{original.get('body_text') or original.get('snippet') or ''}"
            ).strip()
        return self.send_message(
            to=to,
            subject=subject,
            body_text=fwd_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
        )

    def trash_message(self, message_id: str) -> Dict[str, Any]:
        try:
            msg = self.service.users().messages().trash(userId=self._user, id=message_id).execute()
            return {"id": msg.get("id"), "thread_id": msg.get("threadId"), "label_ids": msg.get("labelIds") or []}
        except HttpError as e:
            raise normalize_google_error(e) from e

    def untrash_message(self, message_id: str) -> Dict[str, Any]:
        try:
            msg = self.service.users().messages().untrash(userId=self._user, id=message_id).execute()
            return {"id": msg.get("id"), "thread_id": msg.get("threadId"), "label_ids": msg.get("labelIds") or []}
        except HttpError as e:
            raise normalize_google_error(e) from e

    def delete_message(self, message_id: str) -> None:
        """Permanent delete. Requires broader scope (mail.google.com) than gmail.modify."""
        try:
            self.service.users().messages().delete(userId=self._user, id=message_id).execute()
        except HttpError as e:
            raise normalize_google_error(e) from e

    def modify_message(
        self,
        message_id: str,
        add_label_ids: Optional[List[str]] = None,
        remove_label_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        try:
            body: Dict[str, Any] = {}
            if add_label_ids:
                body["addLabelIds"] = add_label_ids
            if remove_label_ids:
                body["removeLabelIds"] = remove_label_ids
            if not body:
                raise GmailValidationError("Provide add_label_ids and/or remove_label_ids")
            msg = (
                self.service.users()
                .messages()
                .modify(userId=self._user, id=message_id, body=body)
                .execute()
            )
            return {"id": msg.get("id"), "thread_id": msg.get("threadId"), "label_ids": msg.get("labelIds") or []}
        except HttpError as e:
            raise normalize_google_error(e) from e

    def mark_message_read(self, message_id: str) -> Dict[str, Any]:
        return self.modify_message(message_id, remove_label_ids=["UNREAD"])

    def mark_message_unread(self, message_id: str) -> Dict[str, Any]:
        return self.modify_message(message_id, add_label_ids=["UNREAD"])

    # ---- Threads ----

    def list_threads(
        self,
        q: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
        max_results: int = 25,
        page_token: Optional[str] = None,
        include_spam_trash: bool = False,
    ) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[int]]:
        try:
            kwargs: Dict[str, Any] = {
                "userId": self._user,
                "maxResults": min(max(1, max_results), 500),
                "includeSpamTrash": include_spam_trash,
            }
            if q:
                kwargs["q"] = q
            if label_ids:
                kwargs["labelIds"] = label_ids
            if page_token:
                kwargs["pageToken"] = page_token
            result = self.service.users().threads().list(**kwargs).execute()
            threads = result.get("threads") or []
            return threads, result.get("nextPageToken"), result.get("resultSizeEstimate")
        except HttpError as e:
            raise normalize_google_error(e) from e

    def get_thread(self, thread_id: str, format: str = "full") -> Dict[str, Any]:
        try:
            fmt = format if format in ("full", "metadata", "minimal") else "full"
            thr = (
                self.service.users()
                .threads()
                .get(userId=self._user, id=thread_id, format=fmt)
                .execute()
            )
            messages = [
                _normalize_message(m, include_body=fmt == "full")
                for m in thr.get("messages") or []
            ]
            return {
                "id": thr.get("id"),
                "history_id": thr.get("historyId"),
                "snippet": thr.get("snippet"),
                "messages": messages,
            }
        except HttpError as e:
            raise normalize_google_error(e) from e

    def trash_thread(self, thread_id: str) -> Dict[str, Any]:
        try:
            thr = self.service.users().threads().trash(userId=self._user, id=thread_id).execute()
            return {"id": thr.get("id")}
        except HttpError as e:
            raise normalize_google_error(e) from e

    def untrash_thread(self, thread_id: str) -> Dict[str, Any]:
        try:
            thr = self.service.users().threads().untrash(userId=self._user, id=thread_id).execute()
            return {"id": thr.get("id")}
        except HttpError as e:
            raise normalize_google_error(e) from e

    def delete_thread(self, thread_id: str) -> None:
        try:
            self.service.users().threads().delete(userId=self._user, id=thread_id).execute()
        except HttpError as e:
            raise normalize_google_error(e) from e

    def modify_thread(
        self,
        thread_id: str,
        add_label_ids: Optional[List[str]] = None,
        remove_label_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        try:
            body: Dict[str, Any] = {}
            if add_label_ids:
                body["addLabelIds"] = add_label_ids
            if remove_label_ids:
                body["removeLabelIds"] = remove_label_ids
            if not body:
                raise GmailValidationError("Provide add_label_ids and/or remove_label_ids")
            thr = (
                self.service.users()
                .threads()
                .modify(userId=self._user, id=thread_id, body=body)
                .execute()
            )
            return {"id": thr.get("id")}
        except HttpError as e:
            raise normalize_google_error(e) from e

    # ---- Drafts ----

    def list_drafts(
        self,
        max_results: int = 25,
        page_token: Optional[str] = None,
        q: Optional[str] = None,
    ) -> Tuple[List[DraftInfo], Optional[str]]:
        try:
            kwargs: Dict[str, Any] = {
                "userId": self._user,
                "maxResults": min(max(1, max_results), 500),
            }
            if page_token:
                kwargs["pageToken"] = page_token
            if q:
                kwargs["q"] = q
            result = self.service.users().drafts().list(**kwargs).execute()
            drafts = []
            for d in result.get("drafts") or []:
                msg = d.get("message") or {}
                drafts.append(
                    DraftInfo(
                        id=d["id"],
                        message_id=msg.get("id"),
                        thread_id=msg.get("threadId"),
                        snippet=msg.get("snippet"),
                    )
                )
            return drafts, result.get("nextPageToken")
        except HttpError as e:
            raise normalize_google_error(e) from e

    def get_draft(self, draft_id: str, format: str = "full") -> Dict[str, Any]:
        try:
            fmt = format if format in ("full", "metadata", "minimal") else "full"
            draft = (
                self.service.users()
                .drafts()
                .get(userId=self._user, id=draft_id, format=fmt)
                .execute()
            )
            msg = draft.get("message") or {}
            return {
                "id": draft.get("id"),
                "message": _normalize_message(msg, include_body=fmt == "full") if msg else None,
            }
        except HttpError as e:
            raise normalize_google_error(e) from e

    def create_draft(
        self,
        to: Optional[str] = None,
        subject: Optional[str] = None,
        body_text: Optional[str] = None,
        body_html: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        attachments: Optional[List[Dict[str, str]]] = None,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            raw, tid = self._build_mime(
                to=to,
                cc=cc,
                bcc=bcc,
                subject=subject or "",
                body_text=body_text,
                body_html=body_html,
                attachments=attachments,
                thread_id=thread_id,
            )
            message: Dict[str, Any] = {"raw": raw}
            if tid:
                message["threadId"] = tid
            draft = (
                self.service.users()
                .drafts()
                .create(userId=self._user, body={"message": message})
                .execute()
            )
            msg = draft.get("message") or {}
            return {
                "id": draft.get("id"),
                "message_id": msg.get("id"),
                "thread_id": msg.get("threadId"),
            }
        except HttpError as e:
            raise normalize_google_error(e) from e

    def update_draft(
        self,
        draft_id: str,
        to: Optional[str] = None,
        subject: Optional[str] = None,
        body_text: Optional[str] = None,
        body_html: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        attachments: Optional[List[Dict[str, str]]] = None,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            raw, tid = self._build_mime(
                to=to,
                cc=cc,
                bcc=bcc,
                subject=subject or "",
                body_text=body_text,
                body_html=body_html,
                attachments=attachments,
                thread_id=thread_id,
            )
            message: Dict[str, Any] = {"raw": raw}
            if tid:
                message["threadId"] = tid
            draft = (
                self.service.users()
                .drafts()
                .update(userId=self._user, id=draft_id, body={"message": message})
                .execute()
            )
            msg = draft.get("message") or {}
            return {
                "id": draft.get("id"),
                "message_id": msg.get("id"),
                "thread_id": msg.get("threadId"),
            }
        except HttpError as e:
            raise normalize_google_error(e) from e

    def send_draft(self, draft_id: str) -> Dict[str, Any]:
        try:
            sent = (
                self.service.users()
                .drafts()
                .send(userId=self._user, body={"id": draft_id})
                .execute()
            )
            return {
                "id": sent.get("id"),
                "thread_id": sent.get("threadId"),
                "label_ids": sent.get("labelIds") or [],
            }
        except HttpError as e:
            raise normalize_google_error(e) from e

    def delete_draft(self, draft_id: str) -> None:
        try:
            self.service.users().drafts().delete(userId=self._user, id=draft_id).execute()
        except HttpError as e:
            raise normalize_google_error(e) from e

    # ---- Labels ----

    def list_labels(self) -> List[LabelInfo]:
        try:
            result = self.service.users().labels().list(userId=self._user).execute()
            return [
                LabelInfo(
                    id=l["id"],
                    name=l.get("name", ""),
                    type=l.get("type"),
                    message_list_visibility=l.get("messageListVisibility"),
                    label_list_visibility=l.get("labelListVisibility"),
                )
                for l in result.get("labels") or []
            ]
        except HttpError as e:
            raise normalize_google_error(e) from e

    def create_label(
        self,
        name: str,
        message_list_visibility: str = "show",
        label_list_visibility: str = "labelShow",
    ) -> LabelInfo:
        try:
            body = {
                "name": name,
                "messageListVisibility": message_list_visibility,
                "labelListVisibility": label_list_visibility,
            }
            label = self.service.users().labels().create(userId=self._user, body=body).execute()
            return LabelInfo(
                id=label["id"],
                name=label.get("name", name),
                type=label.get("type"),
                message_list_visibility=label.get("messageListVisibility"),
                label_list_visibility=label.get("labelListVisibility"),
            )
        except HttpError as e:
            raise normalize_google_error(e) from e

    def update_label(
        self,
        label_id: str,
        name: Optional[str] = None,
        message_list_visibility: Optional[str] = None,
        label_list_visibility: Optional[str] = None,
    ) -> LabelInfo:
        try:
            body: Dict[str, Any] = {}
            if name is not None:
                body["name"] = name
            if message_list_visibility is not None:
                body["messageListVisibility"] = message_list_visibility
            if label_list_visibility is not None:
                body["labelListVisibility"] = label_list_visibility
            if not body:
                raise GmailValidationError("Provide at least one field to update")
            label = (
                self.service.users()
                .labels()
                .patch(userId=self._user, id=label_id, body=body)
                .execute()
            )
            return LabelInfo(
                id=label["id"],
                name=label.get("name", ""),
                type=label.get("type"),
                message_list_visibility=label.get("messageListVisibility"),
                label_list_visibility=label.get("labelListVisibility"),
            )
        except HttpError as e:
            raise normalize_google_error(e) from e

    def delete_label(self, label_id: str) -> None:
        try:
            self.service.users().labels().delete(userId=self._user, id=label_id).execute()
        except HttpError as e:
            raise normalize_google_error(e) from e

    # ---- Attachments ----

    def download_attachment(
        self,
        message_id: str,
        attachment_id: str,
    ) -> Dict[str, Any]:
        try:
            max_bytes = _max_attachment_bytes()
            att = (
                self.service.users()
                .messages()
                .attachments()
                .get(userId=self._user, messageId=message_id, id=attachment_id)
                .execute()
            )
            declared = att.get("size")
            if declared is not None and int(declared) > max_bytes:
                raise GmailValidationError(
                    f"Attachment exceeds GMAIL_MAX_ATTACHMENT_BYTES ({max_bytes})"
                )
            data = att.get("data") or ""
            # Approx decoded size from urlsafe base64 before allocating.
            estimated = (len(data) * 3) // 4
            if estimated > max_bytes:
                raise GmailValidationError(
                    f"Attachment exceeds GMAIL_MAX_ATTACHMENT_BYTES ({max_bytes})"
                )
            pad = "=" * (-len(data) % 4)
            raw = base64.urlsafe_b64decode(data + pad)
            if len(raw) > max_bytes:
                raise GmailValidationError(
                    f"Attachment exceeds GMAIL_MAX_ATTACHMENT_BYTES ({max_bytes})"
                )
            return {
                "message_id": message_id,
                "attachment_id": attachment_id,
                "size": declared or len(raw),
                "content_base64": base64.b64encode(raw).decode("ascii"),
            }
        except HttpError as e:
            raise normalize_google_error(e) from e
