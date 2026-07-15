#!/usr/bin/env python3
"""
OAuth 2.0 connection script for personal Gmail.

Usage:
    1. Enable Gmail API in Google Cloud Console
    2. Create OAuth 2.0 Client ID (Desktop app), save as credentials.json
    3. python scripts/oauth_connect.py
    4. Use token.json as credentials_path for MCP tools
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Error: pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_FILE = Path(__file__).parent.parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent.parent / "token.json"


def main():
    if not CREDENTIALS_FILE.exists():
        print(f"Error: {CREDENTIALS_FILE} not found.")
        print("Create OAuth 2.0 Desktop credentials and save as credentials.json")
        sys.exit(1)

    print("Opening browser for Google sign-in (Gmail scope)...")
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    token_data = {
        "type": "oauth",
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"\nSuccess! Token saved to {TOKEN_FILE}")
    print(f"  credentials_path: {TOKEN_FILE}")


if __name__ == "__main__":
    main()
