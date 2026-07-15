#!/usr/bin/env python3
"""Unit tests for Gmail MCP helpers (no live Google API / no FastMCP required)."""

import base64
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.exceptions import GmailError, GmailValidationError, normalize_google_error
from app.services.gmail_service import (
    GmailService,
    _b64url_encode,
    _get_credentials,
    _max_attachment_bytes,
)


class TestExceptions(unittest.TestCase):
    def test_normalize_401(self):
        err = normalize_google_error(Exception("<HttpError 401 when requesting"))
        self.assertEqual(err.error_code, "AUTH_ERROR")

    def test_normalize_403(self):
        err = normalize_google_error(Exception("403 permission denied"))
        self.assertEqual(err.error_code, "PERMISSION_DENIED")

    def test_normalize_404(self):
        err = normalize_google_error(Exception("404 not found"))
        self.assertEqual(err.error_code, "NOT_FOUND")

    def test_normalize_429(self):
        err = normalize_google_error(Exception("429 rate limit"))
        self.assertEqual(err.error_code, "RATE_LIMIT")
        self.assertTrue(err.retryable)


class TestCredentials(unittest.TestCase):
    def test_missing_credentials(self):
        with self.assertRaises(GmailError) as ctx:
            _get_credentials()
        self.assertEqual(ctx.exception.error_code, "CREDENTIALS_REQUIRED")

    def test_invalid_json(self):
        with self.assertRaises(GmailError) as ctx:
            _get_credentials(credentials_json="{not-json")
        self.assertEqual(ctx.exception.error_code, "INVALID_CREDENTIALS")

    def test_oauth_json(self):
        payload = {
            "type": "oauth",
            "token": "ya29.example",
            "refresh_token": "1//example",
            "client_id": "client.apps.googleusercontent.com",
            "client_secret": "secret",
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": ["https://www.googleapis.com/auth/gmail.modify"],
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            path = f.name
        creds = _get_credentials(credentials_path=path)
        self.assertEqual(creds.client_id, payload["client_id"])


class TestMimeHelpers(unittest.TestCase):
    def test_b64url(self):
        encoded = _b64url_encode(b"hello")
        self.assertNotIn("=", encoded)

    def test_attachment_oversize_before_decode(self):
        os.environ["GMAIL_MAX_ATTACHMENT_BYTES"] = "100"
        self.addCleanup(lambda: os.environ.pop("GMAIL_MAX_ATTACHMENT_BYTES", None))
        # Base64 for >100 bytes of data
        big = base64.b64encode(b"x" * 200).decode("ascii")
        svc = object.__new__(GmailService)
        with self.assertRaises(GmailValidationError):
            svc._build_mime(
                to="a@example.com",
                subject="t",
                body_text="hi",
                attachments=[{"filename": "big.bin", "content_base64": big}],
            )


class TestDownloadSizeGate(unittest.TestCase):
    def test_rejects_declared_size(self):
        os.environ["GMAIL_MAX_ATTACHMENT_BYTES"] = "50"
        self.addCleanup(lambda: os.environ.pop("GMAIL_MAX_ATTACHMENT_BYTES", None))
        svc = object.__new__(GmailService)
        mock_svc = MagicMock()
        mock_svc.users().messages().attachments().get().execute.return_value = {
            "size": 9999,
            "data": base64.urlsafe_b64encode(b"tiny").decode("ascii").rstrip("="),
        }
        svc._service = mock_svc
        svc._user = "me"
        with self.assertRaises(GmailValidationError):
            svc.download_attachment("m1", "a1")


class TestUpdateLabelPatch(unittest.TestCase):
    def test_uses_patch(self):
        svc = object.__new__(GmailService)
        mock_svc = MagicMock()
        mock_svc.users().labels().patch().execute.return_value = {
            "id": "L1",
            "name": "Renamed",
            "type": "user",
        }
        svc._service = mock_svc
        svc._user = "me"
        label = svc.update_label("L1", name="Renamed")
        self.assertEqual(label.name, "Renamed")
        mock_svc.users().labels().patch.assert_called()
        kwargs = mock_svc.users().labels().patch.call_args.kwargs
        self.assertEqual(kwargs.get("body"), {"name": "Renamed"})


class TestOauthUiFlag(unittest.TestCase):
    def test_disabled(self):
        from app.oauth_routes import _oauth_ui_enabled

        os.environ["GMAIL_ENABLE_OAUTH_UI"] = "0"
        self.addCleanup(lambda: os.environ.pop("GMAIL_ENABLE_OAUTH_UI", None))
        self.assertFalse(_oauth_ui_enabled())


class TestToolInventory(unittest.TestCase):
    def test_mcp_server_tool_count_via_ast(self):
        import ast

        src = (ROOT / "app" / "mcp_server.py").read_text()
        tree = ast.parse(src)
        # Count @mcp.tool decorated functions
        count = 0
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and getattr(dec.func, "attr", None) == "tool":
                        count += 1
                    elif isinstance(dec, ast.Attribute) and dec.attr == "tool":
                        count += 1
        self.assertEqual(count, 28, f"expected 28 tools, found {count}")


if __name__ == "__main__":
    unittest.main()
