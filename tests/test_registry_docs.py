"""Gmail tool guides must be complete enough for Deep Agent."""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.capability_bind import registry_docs  # noqa: E402
from app.core.exceptions import DOCUMENTED_ERROR_CODES  # noqa: E402

DOCS = ROOT / "registry_docs"
SERVER = ROOT / "app" / "mcp_server.py"


def mcp_tool_names() -> list[str]:
    tree = ast.parse(SERVER.read_text(encoding="utf-8"))
    names = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(target, ast.Attribute) and target.attr == "tool":
                names.append(node.name)
                break
    return names


class RegistryDocsTest(unittest.TestCase):
    def test_guides_match_mcp_tools_and_error_ssot(self):
        tools = mcp_tool_names()
        self.assertTrue(tools)
        codes = [code for code, _ in DOCUMENTED_ERROR_CODES]
        self.assertIn("GMAIL_ERROR", codes)
        for name in tools:
            path = DOCS / f"{name}.md"
            self.assertTrue(path.is_file(), f"missing {path}")
            text = path.read_text(encoding="utf-8")
            bound = registry_docs(name)
            self.assertEqual(bound, text.strip())
            self.assertIn(f"# {name}", text)
            self.assertIn("| Name | Required | Type | Sample | Meaning |", text)
            self.assertIn("## Error codes", text)
            self.assertIn("## Cases", text)
            self.assertIn("error_code", text)
            self.assertIn("error_message", text)
            self.assertIn("retryable", text)
            self.assertIn("original_provider_error", text)
            self.assertIn("```json", text)
            self.assertNotIn("invalid_argument", text)
            self.assertIn("untrusted", text.lower())
            self.assertIn("Do not invent a token", text)
            self.assertIn("retryable", text)
            self.assertLessEqual(len(text), 24000)
            for code in codes:
                self.assertIn(f"`{code}`", text, f"{name} missing {code}")

    def test_send_message_documents_attachments_shapes(self):
        text = (DOCS / "send_message.md").read_text(encoding="utf-8")
        self.assertIn("content_base64", text)
        self.assertIn("aGVsbG8=", text)
        self.assertIn("user@example.com", text)
        self.assertIn("attachments must be a JSON array of {filename, content_base64, mime_type}", text)
        self.assertNotIn('"credentials_json"', text.split("## Cases", 1)[1])
        self.assertIn("-32602", text)

    def test_list_messages_snippet_always_null(self):
        text = (DOCS / "list_messages.md").read_text(encoding="utf-8")
        self.assertIn('"snippet": null', text)
        self.assertIn("always `null`", text)
        self.assertIn("get_message", text)

    def test_download_attachment_omits_filename(self):
        text = (DOCS / "download_attachment.md").read_text(encoding="utf-8")
        self.assertIn("does not return `filename` / `mime_type`", text)
        self.assertIn("aGVsbG8=", text)
        self.assertNotIn('"filename": null', text)

    def test_shared_error_example_is_credentials_required(self):
        text = (DOCS / "list_labels.md").read_text(encoding="utf-8")
        self.assertIn("CREDENTIALS_REQUIRED", text)
        self.assertIn("Provide credentials_path or credentials_json", text)
        self.assertNotIn("attachments must be a JSON array", text)


if __name__ == "__main__":
    unittest.main()
