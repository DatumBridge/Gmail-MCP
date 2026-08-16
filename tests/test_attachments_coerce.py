"""Unit tests for Gmail MCP attachments coercion (no FastMCP import)."""

from __future__ import annotations

import json
import unittest
from typing import Any, Dict, List, Optional, Tuple


def _coerce_attachments_arg(value: Any) -> Optional[str]:
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
        coerced = _coerce_attachments_arg(attachments)
        return _parse_attachments(coerced)

    if not isinstance(parsed, list):
        return None, {
            "error_code": "VALIDATION_ERROR",
            "error_message": "attachments must be a JSON array",
            "retryable": False,
            "original_provider_error": None,
        }
    if len(parsed) == 0:
        return None, None
    return parsed, None


class TestAttachmentsCoercion(unittest.TestCase):
    def test_empty_list_parse(self):
        parsed, err = _parse_attachments([])
        self.assertIsNone(parsed)
        self.assertIsNone(err)

    def test_list_passthrough(self):
        raw = [{"filename": "a.txt", "content_base64": "YQ==", "mime_type": "text/plain"}]
        parsed, err = _parse_attachments(raw)
        self.assertIsNone(err)
        self.assertEqual(parsed[0]["filename"], "a.txt")

    def test_json_string(self):
        s = '[{"filename":"a.txt","content_base64":"YQ==","mime_type":"text/plain"}]'
        parsed, err = _parse_attachments(s)
        self.assertIsNone(err)
        self.assertEqual(len(parsed or []), 1)

    def test_empty_string(self):
        parsed, err = _parse_attachments("[]")
        self.assertIsNone(parsed)
        self.assertIsNone(err)


if __name__ == "__main__":
    unittest.main()
