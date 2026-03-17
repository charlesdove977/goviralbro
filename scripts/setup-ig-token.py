#!/usr/bin/env python3
"""
One-time Instagram Graph API token setup.

Walks through the Meta OAuth flow to get a long-lived access token
and Instagram Business Account ID. Saves both to .env.

Prerequisites:
  1. Instagram account must be Business or Creator (not Personal)
  2. Instagram account linked to a Facebook Page
  3. Facebook Developer App created at developers.facebook.com
  4. App has instagram_manage_insights permission (requires App Review)

Usage:
  python scripts/setup-ig-token.py

  You'll need your Facebook App ID and App Secret from:
  https://developers.facebook.com/apps/ > Your App > Settings > Basic
"""

import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Missing dependency: pip install requests")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"

GRAPH_API_VERSION = "v21.0"
BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def update_env(key, value):
    """Add or update a key in .env file."""
    lines = []
    found = False

    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.strip().startswith(f"{key}="):
                lines.append(f"{key}={value}")
                found = True
            else:
                lines.append(line)

    if not found:
        lines.append("")
        lines.append(f"# Instagram Graph API")
        lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(lines) + "\n")


def main():
    print("=" * 50)
    print("Instagram Graph API — Token Setup")
    print("=" * 50)
    print()
    print("Before starting, make sure you have:")
    print("  1. A Business or Creator Instagram account")
    print("  2. A Facebook Page linked to your Instagram")
    print("  3. A Facebook Developer App with instagram_manage_insights")
    print()

    app_id = input("Facebook App ID: ").strip()
    app_secret = input("Facebook App Secret: ").strip()

    if not app_id or not app_secret:
        print("ERROR: App ID and Secret are required.")
        sys.exit(1)

    # Step 1: Generate short-lived token via browser
    auth_url = (
        f"https://www.facebook.com/{GRAPH_API_VERSION}/dialog/oauth"
        f"?client_id={app_id}"
        f"&redirect_uri=https://localhost/"
        f"&scope=instagram_basic,instagram_manage_insights,pages_show_list,pages_read_engagement"
        f"&response_type=code"
    )

    print()
    print("Step 1: Open this URL in your browser and authorize:")
    print()
    print(f"  {auth_url}")
    print()
    print("After authorization, you'll be redirected to a localhost URL.")
    print("Copy the FULL redirect URL (it will fail to load — that's expected).")
    print()

    redirect_url = input("Paste the redirect URL here: ").strip()

    # Extract code from redirect URL
    if "code=" not in redirect_url:
        print("ERROR: Could not find authorization code in URL.")
        sys.exit(1)

    code = redirect_url.split("code=")[1].split("&")[0].split("#")[0]

    # Step 2: Exchange code for short-lived token
    print("\nExchanging code for access token...")
    resp = requests.get(
        f"{BASE_URL}/oauth/access_token",
        params={
            "client_id": app_id,
            "client_secret": app_secret,
            "redirect_uri": "https://localhost/",
            "code": code,
        },
        timeout=15,
    )

    if resp.status_code != 200:
        print(f"ERROR: Token exchange failed: {resp.text}")
        sys.exit(1)

    short_token = resp.json()["access_token"]

    # Step 3: Exchange for long-lived token (60 days)
    print("Exchanging for long-lived token (60 days)...")
    resp = requests.get(
        f"{BASE_URL}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_token,
        },
        timeout=15,
    )

    if resp.status_code != 200:
        print(f"ERROR: Long-lived token exchange failed: {resp.text}")
        sys.exit(1)

    long_token = resp.json()["access_token"]
    expires_in = resp.json().get("expires_in", 5184000)  # ~60 days
    days = expires_in // 86400

    # Step 4: Get Instagram Business Account ID
    print("Finding Instagram Business Account...")
    resp = requests.get(
        f"{BASE_URL}/me/accounts",
        params={"access_token": long_token, "fields": "id,name,instagram_business_account"},
        timeout=15,
    )

    if resp.status_code != 200:
        print(f"ERROR: Could not fetch Pages: {resp.text}")
        sys.exit(1)

    pages = resp.json().get("data", [])
    ig_account_id = None

    for page in pages:
        ig = page.get("instagram_business_account")
        if ig:
            ig_account_id = ig["id"]
            print(f"  Found: {page['name']} → Instagram ID: {ig_account_id}")
            break

    if not ig_account_id:
        print("ERROR: No Instagram Business Account found.")
        print("Make sure your Instagram is linked to a Facebook Page.")
        sys.exit(1)

    # Step 5: Save to .env
    update_env("INSTAGRAM_ACCESS_TOKEN", long_token)
    update_env("INSTAGRAM_BUSINESS_ACCOUNT_ID", ig_account_id)
    update_env("INSTAGRAM_APP_ID", app_id)
    update_env("INSTAGRAM_APP_SECRET", app_secret)

    print()
    print("=" * 50)
    print("Setup complete!")
    print(f"  Token expires in ~{days} days")
    print(f"  Instagram Account ID: {ig_account_id}")
    print(f"  Saved to: {ENV_PATH}")
    print()
    print("Token refresh: run scripts/refresh-ig-token.sh before expiry")
    print("=" * 50)


if __name__ == "__main__":
    main()
