#!/usr/bin/env python3
"""
Fetch per-video YouTube analytics (CTR, watch time, subscribers gained).

Combines:
  - YouTube Data API v3 (views, likes, comments, duration, thumbnail)
  - YouTube Analytics API (CTR, avg view duration, watch time, subs gained)

Auto-detects format from video duration:
  > 180s = youtube_longform, <= 180s = youtube_shorts

Usage:
  python scripts/fetch-yt-analytics.py --video-id VIDEO_ID
  python scripts/fetch-yt-analytics.py --video-id VIDEO_ID --json  # raw JSON output

Requires:
  - YOUTUBE_DATA_API_KEY in .env
  - OAuth token at ~/.viral-command/yt-token.json (run setup-yt-oauth.py first)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("Missing dependency: pip install requests")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"
TOKEN_PATH = Path.home() / ".viral-command" / "yt-token.json"


def load_env():
    """Load .env file into environment."""
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def get_oauth_token():
    """Load and refresh OAuth token if needed."""
    if not TOKEN_PATH.exists():
        return None

    token_data = json.loads(TOKEN_PATH.read_text())

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = Credentials(
            token=token_data["token"],
            refresh_token=token_data["refresh_token"],
            token_uri=token_data["token_uri"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            scopes=token_data.get("scopes"),
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_data["token"] = creds.token
            TOKEN_PATH.write_text(json.dumps(token_data, indent=2))

        return creds.token
    except Exception as e:
        print(f"Warning: OAuth token refresh failed: {e}", file=sys.stderr)
        return token_data.get("token")


def parse_iso8601_duration(duration_str):
    """Parse ISO 8601 duration (PT2M45S) to seconds."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def fetch_data_api(video_id, api_key):
    """Fetch video metadata from YouTube Data API v3."""
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "statistics,snippet,contentDetails",
        "id": video_id,
        "key": api_key,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if not data.get("items"):
        return None

    item = data["items"][0]
    stats = item.get("statistics", {})
    snippet = item.get("snippet", {})
    content = item.get("contentDetails", {})

    duration_sec = parse_iso8601_duration(content.get("duration", "PT0S"))

    # Thumbnail fallback chain
    thumbs = snippet.get("thumbnails", {})
    thumbnail_url = None
    for size in ["maxres", "high", "medium", "default"]:
        if size in thumbs:
            thumbnail_url = thumbs[size]["url"]
            break

    return {
        "title": snippet.get("title"),
        "published_at": snippet.get("publishedAt"),
        "duration_seconds": duration_sec,
        "format": "youtube_longform" if duration_sec > 180 else "youtube_shorts",
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0)),
        "thumbnail_url": thumbnail_url,
    }


def fetch_analytics_api(video_id, published_at, oauth_token):
    """Fetch per-video analytics from YouTube Analytics API."""
    if not oauth_token:
        return {}

    # Parse published date for startDate
    pub_date = published_at[:10] if published_at else "2020-01-01"
    end_date = datetime.utcnow().strftime("%Y-%m-%d")

    url = "https://youtubeanalytics.googleapis.com/v2/reports"
    params = {
        "ids": "channel==MINE",
        "startDate": pub_date,
        "endDate": end_date,
        "metrics": "estimatedMinutesWatched,averageViewDuration,subscribersGained",
        "filters": f"video=={video_id}",
    }
    headers = {"Authorization": f"Bearer {oauth_token}"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        rows = data.get("rows", [])
        if not rows:
            return {}

        row = rows[0]
        return {
            "estimated_minutes_watched": row[0] if len(row) > 0 else None,
            "avg_view_duration": row[1] if len(row) > 1 else None,
            "subscribers_gained": row[2] if len(row) > 2 else None,
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print("Warning: YouTube Analytics API not enabled or not authorized.", file=sys.stderr)
            print("Run: python scripts/setup-yt-oauth.py", file=sys.stderr)
        else:
            print(f"Warning: YouTube Analytics API error: {e}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"Warning: YouTube Analytics API error: {e}", file=sys.stderr)
        return {}


def fetch_ctr(video_id, published_at, oauth_token):
    """Fetch CTR separately (different metric group in Analytics API)."""
    if not oauth_token:
        return None

    pub_date = published_at[:10] if published_at else "2020-01-01"
    end_date = datetime.utcnow().strftime("%Y-%m-%d")

    url = "https://youtubeanalytics.googleapis.com/v2/reports"
    params = {
        "ids": "channel==MINE",
        "startDate": pub_date,
        "endDate": end_date,
        "metrics": "cardClickRate",
        "filters": f"video=={video_id}",
    }
    headers = {"Authorization": f"Bearer {oauth_token}"}

    try:
        # Try impressionClickRate (thumbnail CTR) via content owner reports
        # The standard Analytics API doesn't expose thumbnail CTR directly.
        # We'll try the annotationClickThroughRate as a proxy,
        # but realistically thumbnail CTR requires YouTube Studio.
        params["metrics"] = "views"  # Placeholder — see note below
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        # Note: YouTube Analytics API does NOT expose thumbnail impression CTR
        # (impressionClickThroughRate). That metric is only in YouTube Studio.
        # We return None and fall back to user input for CTR.
        return None
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube video analytics")
    parser.add_argument("--video-id", required=True, help="YouTube video ID")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    load_env()
    api_key = os.environ.get("YOUTUBE_DATA_API_KEY")
    if not api_key or api_key == "your_youtube_data_api_key_here":
        print("ERROR: YOUTUBE_DATA_API_KEY not set in .env")
        sys.exit(1)

    # Fetch Data API (always available)
    data_result = fetch_data_api(args.video_id, api_key)
    if not data_result:
        print(f"ERROR: Video not found: {args.video_id}")
        sys.exit(1)

    # Fetch Analytics API (requires OAuth)
    oauth_token = get_oauth_token()
    analytics_result = {}
    if oauth_token:
        analytics_result = fetch_analytics_api(
            args.video_id, data_result["published_at"], oauth_token
        )

    # Merge results
    result = {
        "video_id": args.video_id,
        "title": data_result["title"],
        "published_at": data_result["published_at"],
        "format": data_result["format"],
        "duration_seconds": data_result["duration_seconds"],
        "thumbnail_url": data_result["thumbnail_url"],
        "metrics": {
            "views": data_result["views"],
            "likes": data_result["likes"],
            "comments": data_result["comments"],
        },
        "analytics_api_available": bool(oauth_token and analytics_result),
    }

    # Add Analytics API metrics if available
    if analytics_result:
        if analytics_result.get("avg_view_duration") is not None:
            result["metrics"]["avg_view_duration"] = analytics_result["avg_view_duration"]
        if analytics_result.get("estimated_minutes_watched") is not None:
            result["metrics"]["estimated_minutes_watched"] = analytics_result["estimated_minutes_watched"]
        if analytics_result.get("subscribers_gained") is not None:
            result["metrics"]["subscribers_gained"] = int(analytics_result["subscribers_gained"])

    # CTR note: not available via Analytics API, requires Studio
    result["metrics"]["ctr"] = None
    result["ctr_note"] = "CTR not available via API — requires YouTube Studio input"

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Video: {result['title']}")
        print(f"Format: {result['format']} ({result['duration_seconds']}s)")
        print(f"Published: {result['published_at']}")
        print(f"Views: {result['metrics']['views']:,}")
        print(f"Likes: {result['metrics']['likes']:,}")
        print(f"Comments: {result['metrics']['comments']:,}")
        if result["metrics"].get("avg_view_duration"):
            mins = int(result["metrics"]["avg_view_duration"]) // 60
            secs = int(result["metrics"]["avg_view_duration"]) % 60
            print(f"Avg View Duration: {mins}:{secs:02d}")
        if result["metrics"].get("estimated_minutes_watched"):
            print(f"Total Watch Time: {result['metrics']['estimated_minutes_watched']:,.0f} minutes")
        if result["metrics"].get("subscribers_gained") is not None:
            print(f"Subscribers Gained: {result['metrics']['subscribers_gained']}")
        if result["analytics_api_available"]:
            print("\n[YouTube Analytics API: active]")
        else:
            print("\n[YouTube Analytics API: not configured — run setup-yt-oauth.py for CTR/subs/watch time]")

    return result


if __name__ == "__main__":
    main()
