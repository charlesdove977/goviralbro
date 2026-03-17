#!/usr/bin/env python3
"""
One-time YouTube OAuth setup for YouTube Analytics API.
Opens browser for authorization, saves token to ~/.viral-command/yt-token.json.

Prerequisites:
  1. Enable YouTube Analytics API in Google Cloud Console
  2. Create OAuth 2.0 Desktop App credentials
  3. Download client_secret.json to scripts/client_secret.json

Usage:
  python scripts/setup-yt-oauth.py
"""

import json
import os
import sys
from pathlib import Path

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Missing dependency: pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CLIENT_SECRET = SCRIPT_DIR / "client_secret.json"
TOKEN_DIR = Path.home() / ".viral-command"
TOKEN_PATH = TOKEN_DIR / "yt-token.json"


def main():
    if not CLIENT_SECRET.exists():
        print(f"ERROR: {CLIENT_SECRET} not found.")
        print()
        print("To set up YouTube OAuth:")
        print("  1. Go to https://console.cloud.google.com/apis/credentials")
        print("  2. Create OAuth 2.0 Client ID (Desktop App)")
        print("  3. Download the JSON and save as: scripts/client_secret.json")
        sys.exit(1)

    print("Starting YouTube OAuth flow...")
    print("A browser window will open for authorization.\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRET), scopes=SCOPES
    )
    credentials = flow.run_local_server(port=8080)

    TOKEN_DIR.mkdir(parents=True, exist_ok=True)

    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes),
    }

    TOKEN_PATH.write_text(json.dumps(token_data, indent=2))
    print(f"\nToken saved to {TOKEN_PATH}")
    print("YouTube Analytics API is ready. Future pulls will use this token silently.")


if __name__ == "__main__":
    main()
