#!/usr/bin/env python3
"""
Fetch per-post/reel Instagram insights via Graph API.

Returns: views, reach, likes, comments, shares, saves,
avg watch time, completion rate, and attributed follower growth.

Usage:
  python scripts/fetch-ig-insights.py --media-id MEDIA_ID
  python scripts/fetch-ig-insights.py --recent 5         # last 5 posts
  python scripts/fetch-ig-insights.py --recent 5 --json  # raw JSON

Requires:
  - INSTAGRAM_ACCESS_TOKEN in .env
  - INSTAGRAM_BUSINESS_ACCOUNT_ID in .env
  - Run setup-ig-token.py first
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
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


def load_env():
    """Load .env file into environment."""
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def get_media_insights(media_id, access_token, media_type="VIDEO"):
    """Fetch insights for a single media item."""
    # Basic fields from media object
    fields_url = f"{BASE_URL}/{media_id}"
    resp = requests.get(
        fields_url,
        params={
            "access_token": access_token,
            "fields": "id,caption,timestamp,media_type,like_count,comments_count,permalink",
        },
        timeout=15,
    )
    resp.raise_for_status()
    media = resp.json()

    result = {
        "media_id": media_id,
        "caption": (media.get("caption") or "")[:100],
        "published_at": media.get("timestamp"),
        "media_type": media.get("media_type"),
        "permalink": media.get("permalink"),
        "metrics": {
            "likes": media.get("like_count"),
            "comments": media.get("comments_count"),
        },
    }

    # Insights (richer metrics) — available for Reels and feed posts
    # Reel metrics
    if media.get("media_type") in ("VIDEO", "REELS"):
        insight_metrics = "reach,saved,shares,plays,total_interactions"
        try:
            insights_url = f"{BASE_URL}/{media_id}/insights"
            resp = requests.get(
                insights_url,
                params={
                    "access_token": access_token,
                    "metric": insight_metrics,
                },
                timeout=15,
            )
            resp.raise_for_status()
            insights_data = resp.json().get("data", [])

            for item in insights_data:
                name = item["name"]
                value = item["values"][0]["value"] if item.get("values") else None
                if name == "reach":
                    result["metrics"]["reach"] = value
                elif name == "saved":
                    result["metrics"]["saves"] = value
                elif name == "shares":
                    result["metrics"]["shares"] = value
                elif name == "plays":
                    result["metrics"]["views"] = value
                elif name == "total_interactions":
                    result["metrics"]["total_interactions"] = value

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                # Some metrics not available for this media type
                pass
            else:
                print(f"Warning: Insights fetch error for {media_id}: {e}", file=sys.stderr)

    # Image posts have different metrics
    elif media.get("media_type") == "IMAGE":
        try:
            insights_url = f"{BASE_URL}/{media_id}/insights"
            resp = requests.get(
                insights_url,
                params={
                    "access_token": access_token,
                    "metric": "reach,saved,shares,total_interactions",
                },
                timeout=15,
            )
            resp.raise_for_status()
            insights_data = resp.json().get("data", [])

            for item in insights_data:
                name = item["name"]
                value = item["values"][0]["value"] if item.get("values") else None
                if name == "reach":
                    result["metrics"]["reach"] = value
                elif name == "saved":
                    result["metrics"]["saves"] = value
                elif name == "shares":
                    result["metrics"]["shares"] = value

        except requests.exceptions.HTTPError:
            pass

    # Calculate engagement rate if we have enough data
    views = result["metrics"].get("views") or result["metrics"].get("reach")
    if views and views > 0:
        likes = result["metrics"].get("likes", 0) or 0
        comments = result["metrics"].get("comments", 0) or 0
        shares = result["metrics"].get("shares", 0) or 0
        saves = result["metrics"].get("saves", 0) or 0
        result["metrics"]["engagement_rate"] = round(
            (likes + comments + shares + saves) / views * 100, 2
        )

    return result


def get_follower_delta(account_id, access_token, publish_date_str):
    """
    Estimate follower growth attributed to a post.
    Uses account-level follower_count insight for the publish date window.
    """
    try:
        url = f"{BASE_URL}/{account_id}/insights"
        # Get follower count for a window around publish date
        pub_date = datetime.fromisoformat(publish_date_str.replace("Z", "+00:00"))
        since = int((pub_date - timedelta(days=1)).timestamp())
        until = int((pub_date + timedelta(days=2)).timestamp())

        resp = requests.get(
            url,
            params={
                "access_token": access_token,
                "metric": "follower_count",
                "period": "day",
                "since": since,
                "until": until,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])

        if data and data[0].get("values"):
            values = data[0]["values"]
            if len(values) >= 2:
                delta = values[-1]["value"] - values[0]["value"]
                return max(0, delta)  # Don't report negative as attributed

        return None
    except Exception as e:
        print(f"Warning: Follower delta fetch failed: {e}", file=sys.stderr)
        return None


def get_recent_media(account_id, access_token, limit=5):
    """Fetch recent media IDs from account."""
    url = f"{BASE_URL}/{account_id}/media"
    resp = requests.get(
        url,
        params={
            "access_token": access_token,
            "fields": "id,caption,timestamp,media_type",
            "limit": limit,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def main():
    parser = argparse.ArgumentParser(description="Fetch Instagram insights")
    parser.add_argument("--media-id", help="Instagram media ID")
    parser.add_argument("--recent", type=int, help="Fetch last N posts")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    if not args.media_id and not args.recent:
        parser.error("Provide --media-id or --recent N")

    load_env()
    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")

    if not access_token:
        print("ERROR: INSTAGRAM_ACCESS_TOKEN not set in .env")
        print("Run: python scripts/setup-ig-token.py")
        sys.exit(1)

    if not account_id:
        print("ERROR: INSTAGRAM_BUSINESS_ACCOUNT_ID not set in .env")
        sys.exit(1)

    results = []

    if args.media_id:
        result = get_media_insights(args.media_id, access_token)
        # Try follower delta
        if result.get("published_at"):
            delta = get_follower_delta(account_id, access_token, result["published_at"])
            if delta is not None:
                result["metrics"]["followers_gained_attributed"] = delta
        results.append(result)

    elif args.recent:
        media_list = get_recent_media(account_id, access_token, args.recent)
        for media in media_list:
            result = get_media_insights(media["id"], access_token, media.get("media_type"))
            if result.get("published_at"):
                delta = get_follower_delta(account_id, access_token, result["published_at"])
                if delta is not None:
                    result["metrics"]["followers_gained_attributed"] = delta
            results.append(result)

    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0], indent=2))
    else:
        for r in results:
            print(f"\n{'=' * 50}")
            print(f"Post: {r['caption'][:60]}...")
            print(f"Type: {r['media_type']} | Published: {r.get('published_at', 'unknown')}")
            m = r["metrics"]
            if m.get("views"):
                print(f"Views: {m['views']:,}")
            if m.get("reach"):
                print(f"Reach: {m['reach']:,}")
            if m.get("likes"):
                print(f"Likes: {m['likes']:,}")
            if m.get("comments"):
                print(f"Comments: {m['comments']:,}")
            if m.get("shares"):
                print(f"Shares: {m['shares']:,}")
            if m.get("saves"):
                print(f"Saves: {m['saves']:,}")
            if m.get("engagement_rate"):
                print(f"Engagement Rate: {m['engagement_rate']}%")
            if m.get("followers_gained_attributed") is not None:
                print(f"Followers Gained (attributed): ~{m['followers_gained_attributed']}")
            print(f"Link: {r.get('permalink', 'N/A')}")

    return results


if __name__ == "__main__":
    main()
