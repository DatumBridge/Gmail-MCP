"""
OAuth 2.0 routes for web-based connection to personal Gmail.

Local-dev / operator connect flow. Disable in production with
GMAIL_ENABLE_OAUTH_UI=0 (Dockerfile default). Prefer scripts/oauth_connect.py
or Studio-managed credentials when UI is off.
"""

import json
import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse

_oauth_tokens: dict[str, dict] = {}
_OAUTH_TTL_SECONDS = 600
_OAUTH_MAX_PENDING = 128

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def _oauth_ui_enabled() -> bool:
    raw = os.environ.get("GMAIL_ENABLE_OAUTH_UI", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _oauth_disabled_response():
    return JSONResponse(
        {
            "error_code": "OAUTH_UI_DISABLED",
            "error_message": "OAuth/test UI disabled. Set GMAIL_ENABLE_OAUTH_UI=1 for local connect, "
            "or use scripts/oauth_connect.py.",
            "retryable": False,
        },
        status_code=404,
    )


def _purge_oauth_state() -> None:
    now = time.time()
    expired = [
        k
        for k, v in _oauth_tokens.items()
        if now - float(v.get("_created_at", now)) > _OAUTH_TTL_SECONDS
    ]
    for k in expired:
        _oauth_tokens.pop(k, None)
    # Bound memory if flood of starts
    if len(_oauth_tokens) > _OAUTH_MAX_PENDING:
        oldest = sorted(
            _oauth_tokens.items(), key=lambda kv: float(kv[1].get("_created_at", 0))
        )
        for k, _ in oldest[: len(_oauth_tokens) - _OAUTH_MAX_PENDING]:
            _oauth_tokens.pop(k, None)


def _get_oauth_config() -> tuple[str, str]:
    creds_path = os.environ.get("GOOGLE_OAUTH_CREDENTIALS") or str(
        Path(__file__).resolve().parent.parent / "credentials.json"
    )
    if os.path.exists(creds_path):
        with open(creds_path) as f:
            data = json.load(f)
        client = data.get("web") or data.get("installed") or {}
        client_id = client.get("client_id") or os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
        client_secret = client.get("client_secret") or os.environ.get(
            "GOOGLE_OAUTH_CLIENT_SECRET"
        )
        return client_id or "", client_secret or ""
    return (
        os.environ.get("GOOGLE_OAUTH_CLIENT_ID", ""),
        os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", ""),
    )


def _get_base_url(request: Request) -> str:
    if os.environ.get("OAUTH_REDIRECT_URI"):
        uri = os.environ["OAUTH_REDIRECT_URI"].rstrip("/")
        return uri.replace("/oauth/callback", "") if "/oauth/callback" in uri else uri
    return str(request.base_url).rstrip("/")


def _get_redirect_uri(request: Request) -> str:
    if os.environ.get("OAUTH_REDIRECT_URI"):
        return os.environ["OAUTH_REDIRECT_URI"].rstrip("/")
    return f"{_get_base_url(request)}/oauth/callback"


async def oauth_start(request: Request):
    if not _oauth_ui_enabled():
        return _oauth_disabled_response()
    _purge_oauth_state()
    client_id, client_secret = _get_oauth_config()
    if not client_id or not client_secret:
        return JSONResponse(
            {
                "error": "OAuth not configured. Add credentials.json (web client) "
                "or GOOGLE_OAUTH_CLIENT_ID/SECRET."
            },
            status_code=500,
        )
    redirect_uri = _get_redirect_uri(request)
    state = secrets.token_urlsafe(32)
    _oauth_tokens[state] = {"status": "pending", "_created_at": time.time()}
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    response = RedirectResponse(url)
    # Bind state to httpOnly cookie to reduce CSRF / stolen-URL redemption.
    response.set_cookie(
        "gmail_oauth_state",
        state,
        httponly=True,
        samesite="lax",
        max_age=_OAUTH_TTL_SECONDS,
        path="/",
    )
    return response


async def oauth_callback(request: Request):
    if not _oauth_ui_enabled():
        return _oauth_disabled_response()
    _purge_oauth_state()
    base_url = _get_base_url(request)
    redirect_uri = _get_redirect_uri(request)
    state = request.query_params.get("state")
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    cookie_state = request.cookies.get("gmail_oauth_state")

    if error:
        return RedirectResponse(f"{base_url}/test?oauth_error={error}")
    if not state or not code:
        return RedirectResponse(f"{base_url}/test?oauth_error=missing_params")
    if not cookie_state or cookie_state != state:
        return RedirectResponse(f"{base_url}/test?oauth_error=state_mismatch")
    if state not in _oauth_tokens:
        return RedirectResponse(f"{base_url}/test?oauth_error=invalid_state")

    client_id, client_secret = _get_oauth_config()
    if not client_id or not client_secret:
        return RedirectResponse(f"{base_url}/test?oauth_error=config")

    try:
        import requests

        body = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        resp.raise_for_status()
        token_data = resp.json()
    except Exception:
        return RedirectResponse(f"{base_url}/test?oauth_error=exchange")

    # Store full OAuth material server-side only until one-shot redeem.
    oauth_creds = {
        "type": "oauth",
        "token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": SCOPES,
        "_created_at": time.time(),
    }
    _oauth_tokens[state] = oauth_creds
    return RedirectResponse(f"{base_url}/test?oauth={state}")


async def oauth_token(request: Request):
    """One-shot token redeem. Requires matching httpOnly state cookie."""
    if not _oauth_ui_enabled():
        return _oauth_disabled_response()
    _purge_oauth_state()
    state = request.query_params.get("state")
    cookie_state = request.cookies.get("gmail_oauth_state")
    if not state or state not in _oauth_tokens:
        return JSONResponse({"error": "Invalid or expired state"}, status_code=400)
    if not cookie_state or cookie_state != state:
        return JSONResponse({"error": "OAuth state cookie required"}, status_code=403)
    data = _oauth_tokens.pop(state)
    if data.get("status") == "pending":
        return JSONResponse({"error": "OAuth not complete"}, status_code=400)
    # Return user token material for local test UI / credentials_json.
    # client_secret is required for refresh with google-auth; only returned when
    # redeeming with valid cookie after OAuth UI was explicitly enabled.
    payload = {k: v for k, v in data.items() if not k.startswith("_")}
    response = JSONResponse(payload)
    response.delete_cookie("gmail_oauth_state", path="/")
    return response


async def oauth_info(request: Request):
    if not _oauth_ui_enabled():
        return _oauth_disabled_response()
    redirect_uri = _get_redirect_uri(request)
    return JSONResponse(
        {
            "redirect_uri": redirect_uri,
            "scopes": SCOPES,
            "instruction": "Add this EXACT URL to Google Cloud Console → Credentials "
            "→ OAuth 2.0 Client → Authorized redirect URIs. Enable Gmail API. "
            "Local-dev only: set GMAIL_ENABLE_OAUTH_UI=0 in production images.",
        }
    )
