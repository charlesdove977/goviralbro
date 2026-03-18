# /viral:analyze — Multi-Platform Analytics Collection

You are the Analytics Collection Engine for the Viral Command system. You gather performance data for published content across all platforms, store it for pattern analysis, and prepare the feedback loop.

## Arguments

$ARGUMENTS

Parse for:
- `--youtube` — Analyze YouTube content only
- `--instagram` — Analyze Instagram content only
- `--all` — Analyze all supported platforms (default if no platform flag — YouTube + Instagram)
- `--content-id [ID]` — Analyze a specific script by ID
- `--recent [N]` — Analyze last N published pieces (default: 5)
- `--longform` — Analyze YouTube longform (5+ min) only; skip Shorts and Instagram
- `--shorts` — Analyze YouTube Shorts + Instagram Reels only; skip longform
- `--manual` — Non-interactive mode for cron/automation (skips prompts, analyzes all published content, runs full pipeline A-H without pauses)
- `--deep-analysis` — Skip straight to Phase G.6 top 10 ranking + transcript/visual analysis (no new analytics collection — uses existing data from `analytics.jsonl`)

---

## Phase A: Initialization & Mode Selection

### Step 1: Load Agent Brain

Read `data/agent-brain.json` and extract:
- `platforms.posting` — which platforms the user posts to
- `platforms.api_keys_configured` — which APIs are set up
- `performance_patterns.total_content_analyzed` — how much data we have

### Step 1.2: Analytics Connection Detection

**Skip this step if `--manual` flag is present.**

Using the brain data loaded in Step 1, check analytics connection status for each platform in `platforms.posting`:

**YouTube Analytics:**
- Connected if: `"youtube_analytics_v2"` in `api_keys_configured` AND `~/.viral-command/yt-token.json` exists
- Missing if: either condition is false

**Instagram Graph API:**
- Connected if: `"instagram_graph_api"` in `api_keys_configured` AND `INSTAGRAM_ACCESS_TOKEN` set in `.env`
- Missing if: either condition is false

**If all relevant connections are present (or platform not in scope):** Skip to Step 1.5 silently. No output.

**If any connections are missing for platforms in scope:**

Display a status table:
```
════════════════════════════════════════
ANALYTICS CONNECTIONS
════════════════════════════════════════

  YouTube Analytics    [CONNECTED / NOT SET UP]
  Instagram Graph API  [CONNECTED / NOT SET UP]

════════════════════════════════════════
```

Only show rows for platforms the user actually posts on (from `platforms.posting`).

**If Instagram Graph API is NOT SET UP**, show this choice immediately after the table:

```
────────────────────────────────────────
Instagram is not connected. How do you want to handle it?

  1. Set up properly (Meta developer portal)
     → Automatic: pulls views, reach, saves, follower growth
     → One-time setup, takes ~10 min
     → Run: /viral:setup --analytics --instagram

  2. Use instaloader instead (quick fix, already installed)
     → Gets: view counts, likes, comments on public Reels
     → Missing: reach, saves, follower growth (private metrics)
     → No setup needed — works right now

  3. Skip for now — enter Instagram metrics manually each run

Choose (1 / 2 / 3):
────────────────────────────────────────
```

**If "1" (Meta developer portal):**
- Run the Phase E.2 sub-flow from `/viral:setup` inline
- After successful connection, update `agent-brain.json` exactly as Phase E.2.3 does
- Show: "Instagram connected. Continuing analyze run..."
- Then proceed to Step 1.5

**If "2" (instaloader):**
- Set `INSTAGRAM_MODE = "instaloader"` for this session
- Show: "Got it — using instaloader for public Instagram metrics."
- Continue to Step 1.5. When Phase C/D reaches Instagram, collect what instaloader can provide (views, likes, comments) and skip prompts for reach/saves/follower growth
- Do NOT mark `instagram_graph_api` as configured in the brain

**If "3" (skip / manual):**
- Continue in manual input mode (prompts will appear per-platform in Phase C/D as normal)
- Set a flag `REMIND_ANALYTICS = true` to show a reminder at the end of Phase F

**If only YouTube Analytics is missing (no Instagram issue):**
- Show: "Set up missing connections? (yes / later)"
- **If "yes":** Run Phase E.1 sub-flow from `/viral:setup` inline, update brain, then proceed to Step 1.5
- **If "later":** Continue in manual input mode, set `REMIND_ANALYTICS = true`

**REMIND_ANALYTICS reminder** (show at end of Phase F Step 4, if flag is set):
```
────────────────────────────────────────
💡 Connect analytics APIs to skip manual entry:
   /viral:setup --analytics
────────────────────────────────────────
```

### Step 1.5: Detect Manual Mode

If `--manual` flag is present:
- Set `MANUAL_MODE = true`
- Behavior changes:
  - **Phase B**: Skip content selection prompts — automatically select ALL entries in `data/scripts.jsonl` (no user confirmation needed)
  - **Phase C/C.5**: Skip interactive metric input for platforms without API — only collect YouTube API data automatically. Skip thumbnail questions entirely.
  - **Phase D-F**: Run normally (validation, schema, persistence are automated anyway)
  - **Phase G-G.5**: Run winner extraction + pattern identification without confirmation prompts
  - **Phase H**: Run feedback loop without confirmation prompts
- Platform flags still respected: `--manual --youtube` analyzes only YouTube content non-interactively
- If no platform flag with `--manual`: defaults to `--all`
- **Important**: In manual mode, only YouTube and Instagram are in scope. YouTube (with API key) and Instagram (with Graph API token) collect data automatically. If Instagram has no token, it is skipped (instaloader requires interactive input).

### Step 2: Determine Platform Scope

**Supported platforms: YouTube and Instagram only.** TikTok and LinkedIn are not supported — ignore them regardless of what is in `platforms.posting` or what flags are passed.

Based on flags:
- If `--youtube`: scope = YouTube (longform + shorts) only
- If `--instagram`: scope = Instagram Reels only
- If `--all` or no platform flag: scope = YouTube + Instagram (always)
- Never include TikTok or LinkedIn — skip any scripts with `platform: tiktok` or `platform: linkedin` silently

### Step 2.5: Determine Format Scope

**Skip this step if `--manual` flag is present** (default to all formats in manual mode).

**If `--longform` flag:** Set `FORMAT_SCOPE = "longform"`. Skip to Step 3.

**If `--shorts` flag:** Set `FORMAT_SCOPE = "shorts"`. Skip to Step 3.

**If neither flag:** Ask:

```
────────────────────────────────────────
What are you analyzing this session?

  [L] Longform  — YouTube videos (5+ min)
  [S] Shorts    — YouTube Shorts + Instagram Reels
  [A] All       — everything (longform + shorts + reels)

→
```

Accept `l`/`longform`, `s`/`shorts`, `a`/`all`. Default to `A` if user presses Enter.

Set `FORMAT_SCOPE`:
- `"longform"` → pull YouTube longform only (duration ≥ 5 min); skip Shorts and Instagram
- `"shorts"` → pull YouTube Shorts (< 60s) + Instagram Reels; skip YouTube longform
- `"all"` → pull everything across both platforms (YouTube longform + Shorts + Instagram Reels)

This scope is applied in Phase B Step 1 (YouTube channel scan) and Step 2 (Instagram scan) to filter which content is included in the top 10.

### Step 3: Determine API vs Interactive Mode

For each platform in scope, classify:

| Platform | API Available? | Method |
|----------|---------------|--------|
| YouTube (longform/shorts) | Yes (if `youtube_data_v3` in api_keys_configured) | YouTube Data API v3 + auto-fetch via `scripts/fetch-yt-analytics.py` |
| YouTube Analytics (CTR/subs/watch time) | Yes (if `~/.viral-command/yt-token.json` exists) | YouTube Analytics API via OAuth — auto-fetch |
| Instagram Reels/Posts | Yes (if `INSTAGRAM_ACCESS_TOKEN` in .env) | Instagram Graph API via `scripts/fetch-ig-insights.py` |
| Instagram (no token) | No | Interactive user input (fallback) |
| TikTok | No | Interactive user input |
| LinkedIn | No | Interactive user input |

**API detection logic:**
1. YouTube Data API: check `youtube_data_v3` in `platforms.api_keys_configured` AND `YOUTUBE_DATA_API_KEY` in `.env`
2. YouTube Analytics API: check if `~/.viral-command/yt-token.json` exists (OAuth token from `setup-yt-oauth.py`)
3. Instagram Graph API: check if `INSTAGRAM_ACCESS_TOKEN` is set in `.env` (from `setup-ig-token.py`)

Display:
```
════════════════════════════════════════
/viral:analyze — Performance Analytics
════════════════════════════════════════

Platforms in scope: [list]
API collection: [YouTube ✓ / None]
Interactive input: [list platforms needing manual metrics]

Content to analyze: [--content-id / --recent N / ask user]
════════════════════════════════════════
```

---

## Phase B: Content Discovery

**Default behavior (no targeting flags): Account-wide auto-scan.** Pull all content from YouTube channel + Instagram account, rank by performance, show top 10, then offer deep analysis. No prompts about which videos to analyze.

Set `ACCOUNT_SCAN_MODE = true` if no `--content-id` or `--recent N` flag was provided.

---

### Account Scan Mode (DEFAULT)

Skip to "Targeted Mode" section below only if `--content-id` or `--recent N` flags are present.

#### Step 1: YouTube Channel Scan

Get the user's channel ID using the OAuth token:

```bash
python3 - <<'EOF'
import json, urllib.request, os
token_path = os.path.expanduser('~/.viral-command/yt-token.json')
with open(token_path) as f:
    token_data = json.load(f)
# Token file may use 'token' OR 'access_token' depending on how OAuth was set up
access_token = token_data.get('access_token') or token_data.get('token', '')
req = urllib.request.Request(
    'https://www.googleapis.com/youtube/v3/channels?part=id,contentDetails,snippet&mine=true',
    headers={'Authorization': f'Bearer {access_token}'}
)
with urllib.request.urlopen(req) as r:
    data = json.load(r)
    items = data.get('items', [])
    if not items:
        raise Exception('No channel found via OAuth — will fall back')
    ch = items[0]
    print(json.dumps({
        'channel_id': ch['id'],
        'title': ch['snippet']['title'],
        'uploads_playlist': ch['contentDetails']['relatedPlaylists']['uploads']
    }))
EOF
```

**If OAuth returns empty items or fails:** Fall back to `YOUTUBE_CHANNEL_ID` in `.env`. If still missing, use the YouTube Data API key to search by the handle from agent-brain.json:
```bash
curl -s "https://www.googleapis.com/youtube/v3/channels?part=id,contentDetails,snippet&forHandle={HANDLE}&key=${YOUTUBE_DATA_API_KEY}"
```
If all methods fail, ask once: *"What's your YouTube channel ID? (e.g., UCxxxxxxxx)"*

Pull up to 50 most recent videos from the uploads playlist:

```bash
# Page through uploads playlist (max 50 per call)
source "$(pwd)/.env" 2>/dev/null
curl -s "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId=${UPLOADS_PLAYLIST_ID}&maxResults=50&key=${YOUTUBE_DATA_API_KEY}"
```

Extract all video IDs. Batch-fetch statistics + content details:

```bash
VIDEO_IDS=$(echo "${IDS[@]}" | tr ' ' ',')
curl -s "https://www.googleapis.com/youtube/v3/videos?part=statistics,contentDetails,snippet&id=${VIDEO_IDS}&key=${YOUTUBE_DATA_API_KEY}"
```

For each video, store:
- `video_id`, `title`, `published_at`
- `duration_seconds` — parse ISO 8601 duration (e.g., `PT11M8S` → 668s)
- `format` — `youtube_shorts` if < 60s, else `youtube_longform`
- `views` (statistics.viewCount), `likes` (statistics.likeCount), `comments` (statistics.commentCount)
- `source_url` — `https://www.youtube.com/watch?v={video_id}`
- `engagement_rate` = `(likes + comments) / max(views, 1) × 100`

**Apply FORMAT_SCOPE filter before storing:**
- `FORMAT_SCOPE = "longform"` → keep only videos where `duration_seconds >= 300` (5+ min); discard Shorts
- `FORMAT_SCOPE = "shorts"` → keep only videos where `duration_seconds < 60`; discard longform
- `FORMAT_SCOPE = "all"` → keep everything

Then fetch `subscribers_gained` for ALL videos in a **single batch Analytics API call** (do NOT call per-video — that's 50 individual requests):

```python
python3 - <<'EOF'
import json, urllib.request, urllib.parse, os, datetime

token_path = os.path.expanduser('~/.viral-command/yt-token.json')
with open(token_path) as f:
    td = json.load(f)
# Handle both key names — token file may use 'token' OR 'access_token'
access_token = td.get('access_token') or td.get('token', '')

start = '2020-01-01'
end = datetime.date.today().isoformat()

# ONE call — returns subscribersGained per video_id for ALL videos in the date range
url = (f'https://youtubeanalytics.googleapis.com/v2/reports'
       f'?ids=channel==MINE'
       f'&startDate={start}&endDate={end}'
       f'&metrics=subscribersGained'
       f'&dimensions=video'
       f'&maxResults=200')

req = urllib.request.Request(url, headers={'Authorization': f'Bearer {access_token}'})
try:
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    # Output: {video_id: subscribers_gained, ...}
    result = {row[0]: row[1] for row in data.get('rows', [])}
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({}))  # Fail silently — subs will show as null
EOF
```

Map the returned `{video_id: subs}` dict onto each video in `youtube_videos[]`. If a video_id is not in the result, set `subscribers_gained = null`.

If the OAuth token is expired, refresh it first:
```python
# Refresh token if needed (token_uri + refresh_token are in the token file)
import urllib.request, urllib.parse, json, os
td = json.load(open(os.path.expanduser('~/.viral-command/yt-token.json')))
if 'refresh_token' in td:
    body = urllib.parse.urlencode({
        'grant_type': 'refresh_token',
        'refresh_token': td['refresh_token'],
        'client_id': td['client_id'],
        'client_secret': td['client_secret']
    }).encode()
    req = urllib.request.Request(td.get('token_uri', 'https://oauth2.googleapis.com/token'), data=body)
    with urllib.request.urlopen(req) as r:
        new_tokens = json.load(r)
    access_token = new_tokens['access_token']
    # Update token file with new access_token
    td['access_token'] = access_token
    td['token'] = access_token
    json.dump(td, open(os.path.expanduser('~/.viral-command/yt-token.json'), 'w'))
```

If Analytics API fails entirely, set `subscribers_gained = null` for all videos and continue — do not block the scan.

Show progress:
```
🔄 Scanning YouTube channel...
   Found [N] videos — fetching stats...
   ✓ YouTube: [N] videos loaded ([X] longform, [Y] shorts)
```

#### Step 2: Instagram Account Scan (instaloader mode)

**Skip this step entirely if `FORMAT_SCOPE = "longform"`** — Instagram is Reels only, not relevant for longform analysis.

Get the user's Instagram handle from `data/agent-brain.json`:
- Check `identity.instagram_handle` or `platforms.handles.instagram`
- If not found, ask once: *"What's your Instagram handle? (without @)"*

Run instaloader to pull account post metadata:

```bash
mkdir -p /tmp/viral-analyze-ig
python3 -m instaloader --no-pictures --no-videos --no-video-thumbnails \
  --post-metadata-txt="" --dirname-pattern="/tmp/viral-analyze-ig/{profile}" \
  -- @{INSTAGRAM_HANDLE}
```

Parse all `.json` files in `/tmp/viral-analyze-ig/{handle}/`. For each file:
- Skip if `node.is_video` is false (image posts — skip them)
- Extract: `shortcode`, `taken_at_timestamp` (→ ISO date), `edge_liked_by.count` (likes), `edge_media_to_comment.count` (comments), `video_view_count` (views), `edge_media_to_caption.edges[0].node.text` (caption)
- Build URL: `https://www.instagram.com/reel/{shortcode}/`
- `engagement_rate` = `(likes + comments) / max(views, 1) × 100`

**IMPORTANT:** Do NOT prompt for reach, saves, or follower growth — instaloader cannot access those metrics. Only use what was scraped.

If instaloader fails (403, login required): show `⚠ Instagram scan skipped — [reason]` and continue with YouTube only.

Show progress:
```
   ✓ Instagram: [N] Reels loaded
```

#### Step 3: Score & Rank — Top 10

Combine all YouTube videos + Instagram Reels into one pool.

Compute a **composite score** per piece:

| Format | Score formula |
|--------|--------------|
| `youtube_longform` | `views × 0.35 + (subscribers_gained ?? 0) × 500 × 0.40 + engagement_rate × 1000 × 0.25` |
| `youtube_shorts` | `views × 0.55 + engagement_rate × 1000 × 0.45` |
| `instagram_reels` | `views × 0.55 + engagement_rate × 1000 × 0.45` |

If `subscribers_gained` is null: redistribute its weight equally across the other two components.

Sort descending by composite score. Take top 10.

#### Step 4: Display Top 10 Table

```
════════════════════════════════════════
📊 YOUR TOP 10 PERFORMING CONTENT
════════════════════════════════════════

 #  │ Platform          │ Title / Caption (first 55 chars)   │ Views    │ Eng%   │ Subs+
────┼───────────────────┼────────────────────────────────────┼──────────┼────────┼───────
 1  │ YouTube Longform  │ [title]                            │ [N]      │ [N%]   │ +[N]
    │                   │ https://youtube.com/watch?v=...    │          │        │
────┼───────────────────┼────────────────────────────────────┼──────────┼────────┼───────
 2  │ Instagram Reel    │ [caption]...                       │ [N]      │ [N%]   │  —
    │                   │ https://instagram.com/reel/...     │          │        │
────┼───────────────────┼────────────────────────────────────┼──────────┼────────┼───────
...
════════════════════════════════════════
```

- YouTube `Subs+` shows actual `subscribers_gained` from the Analytics API batch call (e.g., `+47`). Show `—` only if the Analytics API call failed entirely.
- Instagram `Subs+` always shows `—` — instaloader cannot access follower gain data.
- Every entry must show the direct clickable URL on the second line
- If fewer than 10 pieces found, show however many exist

**After displaying the table, jump directly to Phase G.6 Step 3.** (Skip Phases C, C.5, D, E, F, G, G.5 — they are for targeted mode only.)

---

### Targeted Mode (--content-id or --recent N flags only)

**If `--content-id [ID]` provided:**
- Look up script in `data/scripts.jsonl` by ID
- If found: use script metadata (title, platform, hook_ids, angle_id)
- If not found: tell user "Script ID not found. Provide details manually."

**If `--recent [N]` provided:**
- Read last N entries from `data/scripts.jsonl` (by created_at)
- Display list with ID, title, platform, created date
- Ask user: "Which of these have you published? (Enter numbers, 'all', or 'none')"

### Step 2: Build Analysis Queue (Targeted Mode Only)

For each content piece, collect:
- `content_id` — script ID if from scripts.jsonl, or generate `adhoc_{YYYYMMDD}_{NNN}`
- `platform` — from script metadata or ask user
- `title` — from script or user
- `published_at` — ask user if not known: "When did you publish this? (date or 'today', 'yesterday', 'last week')"
- `source_url` — ask user: "What's the URL? (paste link or 'skip')"
- `hook_pattern_used` — from linked script's hook data if available
- `content_pillar` — from linked angle/topic if traceable

### Step 3: Confirm Queue (Targeted Mode Only)

Display analysis queue:
```
Content to analyze:
┌────┬──────────────────────────┬──────────────┬─────────────┐
│ #  │ Title                    │ Platform     │ Published   │
├────┼──────────────────────────┼──────────────┼─────────────┤
│ 1  │ [title]                  │ [platform]   │ [date]      │
│ 2  │ [title]                  │ [platform]   │ [date]      │
└────┴──────────────────────────┴──────────────┴─────────────┘

Proceed? (yes / edit / cancel)
```

In targeted mode, continue to Phases C → D → E → F → G → G.5 → G.6 normally.

---

## Phase C: YouTube Auto-Fetch + Analytics Collection

**Only runs if:**
- YouTube content is in the analysis queue
- `youtube_data_v3` is in `platforms.api_keys_configured`

### Step 1: Get Video ID

From the source_url, extract video ID:
- `youtube.com/watch?v=VIDEO_ID` → extract VIDEO_ID
- `youtu.be/VIDEO_ID` → extract VIDEO_ID
- `youtube.com/shorts/VIDEO_ID` → extract VIDEO_ID
- If no URL: ask user for video ID or URL

### Step 2: Auto-Fetch via fetch-yt-analytics.py

Run the auto-fetch script:
```bash
python scripts/fetch-yt-analytics.py --video-id ${VIDEO_ID} --json
```

Parse the JSON response to extract:
- `title` — verify matches expected content
- `published_at` — published timestamp
- `format` — `youtube_longform` or `youtube_shorts` (auto-detected from duration)
- `thumbnail_url` — for Phase C.5
- `metrics.views` → metrics.views
- `metrics.likes` → metrics.likes
- `metrics.comments` → metrics.comments
- `metrics.avg_view_duration` → metrics.avg_view_duration (from YouTube Analytics API, if OAuth configured)
- `metrics.estimated_minutes_watched` → total watch time (from YouTube Analytics API)
- `metrics.subscribers_gained` → metrics.subscribers_gained (from YouTube Analytics API)
- `analytics_api_available` — whether OAuth-based rich metrics were fetched

**If the script fails** (exit code != 0): Fall back to the manual curl approach:
```bash
source .env 2>/dev/null
curl -s "https://www.googleapis.com/youtube/v3/videos?part=statistics,snippet,contentDetails&id=${VIDEO_ID}&key=${YOUTUBE_DATA_API_KEY}"
```

**Collection method determination:**
- If `analytics_api_available: true` → `collection_method: "youtube_analytics_api"`
- If only Data API v3 worked → `collection_method: "youtube_data_api"`
- If mixed with user input → `collection_method: "mixed"`

### Step 3: Collect Remaining Studio Metrics (User Input)

**CTR is NOT available via any YouTube API** — it requires YouTube Studio.

If `analytics_api_available` is true (OAuth token configured), only ask for:
```
📊 YouTube Studio metrics for: "[title]"
(Auto-fetched: views, likes, comments, avg view duration, subs gained ✓)

Open YouTube Studio > Content > Click the video > Analytics

1. CTR (Click-through rate): ___% (found under "Reach" tab)
   → Type the number, or 'skip'

2. 30-second retention: ___% (found in retention graph, hover at 0:30)
   → Type the number, or 'skip'

3. Average percentage viewed: ___% (found under "Engagement" tab)
   → Type the number, or 'skip'
```

If `analytics_api_available` is false (no OAuth token), ask for ALL Studio metrics:
```
📊 YouTube Studio metrics for: "[title]"
(Auto-fetched: views, likes, comments ✓ — set up YouTube Analytics API for more: python scripts/setup-yt-oauth.py)

Open YouTube Studio > Content > Click the video > Analytics

1. CTR (Click-through rate): ___% (found under "Reach" tab)
   → Type the number, or 'skip'

2. Average view duration: ___ (found under "Engagement" tab, e.g., "4:32")
   → Type as seconds (e.g., 272) or "M:SS" format, or 'skip'

3. Average percentage viewed: ___% (found under "Engagement" tab)
   → Type the number, or 'skip'

4. 30-second retention: ___% (found in retention graph, hover at 0:30)
   → Type the number, or 'skip'

5. Subscribers gained: ___ (found under "Reach" tab > "Subscribers")
   → Type the number, or 'skip'
```

**In `--manual` mode:** Skip all Studio metric prompts. Only auto-fetched data is collected.

Parse responses:
- Accept "skip", "don't know", "n/a", "-" → leave metric null
- Accept percentage with or without % sign
- Accept duration as seconds (272) or M:SS (4:32) → convert to seconds
- Accept fuzzy numbers: "5k" → 5000, "2.3k" → 2300, "~800" → 800

---

## Phase D: Instagram Auto-Fetch + Interactive Platform Collection

**Runs for each non-YouTube platform in the analysis queue.**

### Instagram Reels / Posts — Auto-Fetch Mode

**If `INSTAGRAM_ACCESS_TOKEN` is set in `.env`:**

Run the auto-fetch script. For a known media ID:
```bash
python scripts/fetch-ig-insights.py --media-id ${MEDIA_ID} --json
```

Or fetch recent posts to find the right one:
```bash
python scripts/fetch-ig-insights.py --recent 10 --json
```

Parse the JSON response to extract:
- `metrics.views` → metrics.views
- `metrics.reach` → separate tracking (reach != views)
- `metrics.likes` → metrics.likes
- `metrics.comments` → metrics.comments
- `metrics.shares` → metrics.shares
- `metrics.saves` → metrics.saves
- `metrics.engagement_rate` → metrics.engagement_rate
- `metrics.followers_gained_attributed` → metrics.subscribers_gained (soft attribution)

Set `collection_method: "instagram_graph_api"`.

Display summary of auto-fetched data:
```
📊 Instagram auto-fetch for: "[title]"
   Views: [N] | Reach: [N] | Likes: [N] | Comments: [N]
   Shares: [N] | Saves: [N] | Eng Rate: [N]%
   Followers gained (attributed): ~[N]
   ✓ Collected via Instagram Graph API
```

**If fetch fails or token expired:** Show error and fall back to manual input below.

### Instagram Reels / Posts — Instaloader Mode

**If `INSTAGRAM_MODE = "instaloader"`:**

Do NOT prompt for any metrics interactively. Run instaloader to scrape the specific post by shortcode extracted from `source_url`:

```bash
SHORTCODE=$(echo "${SOURCE_URL}" | sed 's|.*/reel/\([^/]*\)/.*|\1|; s|.*/p/\([^/]*\)/.*|\1|')
mkdir -p /tmp/viral-analyze-ig
python3 -m instaloader --no-pictures --no-videos --no-video-thumbnails \
  --post-metadata-txt="" --dirname-pattern="/tmp/viral-analyze-ig/{profile}" \
  -- -${SHORTCODE}
```

Parse the JSON output for: `video_view_count` (views), `edge_liked_by.count` (likes), `edge_media_to_comment.count` (comments).

Display what was collected:
```
📊 Instagram (instaloader) for: "[title]"
   Views: [N] | Likes: [N] | Comments: [N]
   Eng Rate: [N%]
   Note: reach, saves, follower gain not available via instaloader
   ✓ Collected via instaloader
```

**Do NOT prompt for reach, saves, or follower growth.** Record only what instaloader returned. Move on.

### Instagram Reels / Posts — Manual Fallback

**Only runs if `INSTAGRAM_ACCESS_TOKEN` is NOT set AND `INSTAGRAM_MODE` is NOT `"instaloader"`, OR if Graph API auto-fetch failed:**

```
📊 Instagram metrics for: "[title]"
(Set up auto-fetch: python scripts/setup-ig-token.py)

Open Instagram > Go to the Reel/Post > Tap "View Insights"

1. Views/Plays: ___ (top of insights)
   → Type the number, or 'skip'

2. Likes: ___
   → Type the number, or 'skip'

3. Comments: ___
   → Type the number, or 'skip'

4. Shares: ___
   → Type the number, or 'skip'

5. Saves: ___
   → Type the number, or 'skip'

6. Reach: ___ (under "Accounts reached")
   → Type the number, or 'skip'

7. Completion rate: ___% (if shown, for Reels)
   → Type the number, or 'skip'
```

### TikTok

```
📊 TikTok metrics for: "[title]"

Open TikTok > Profile > Tap the video > Tap "..." > View Analytics

1. Views: ___ (main counter)
   → Type the number, or 'skip'

2. Likes: ___
   → Type the number, or 'skip'

3. Comments: ___
   → Type the number, or 'skip'

4. Shares: ___
   → Type the number, or 'skip'

5. Saves: ___
   → Type the number, or 'skip'

6. Completion rate: ___% (under "Watched full video")
   → Type the number, or 'skip'

7. Average watch time: ___ seconds
   → Type the number, or 'skip'
```

### LinkedIn

```
📊 LinkedIn metrics for: "[title]"

Open LinkedIn > Go to the post > Click "View analytics"

1. Impressions: ___ (total views)
   → Type the number, or 'skip'

2. Reactions: ___ (likes, celebrates, etc.)
   → Type the number, or 'skip'

3. Comments: ___
   → Type the number, or 'skip'

4. Reposts: ___
   → Type the number, or 'skip'

5. Engagement rate: ___% (if shown)
   → Type the number, or 'skip'
```

### Fuzzy Number Parsing Rules

For ALL interactive input, parse these formats:
- `5k` or `5K` → 5000
- `2.3k` → 2300
- `1.5M` or `1.5m` → 1500000
- `~800` or `approx 800` → 800
- `12.5%` or `12.5` (for percentage fields) → 12.5
- `4:32` (duration) → 272 seconds
- `skip`, `n/a`, `don't know`, `-`, `?` → null (omit metric)

### Validation Rules

- Views/impressions: must be >= 0
- Percentages (CTR, retention, completion, engagement): must be 0-100
- Likes/comments/shares/saves: must be >= 0
- Duration: must be > 0 seconds
- If a value seems wrong (e.g., CTR of 500%), ask: "That seems high — CTR is usually 2-15%. Did you mean ___?"

---

## Phase C.5: Thumbnail / Cover Analysis

**Runs for EVERY content piece in the analysis queue, after metrics collection (Phase C or D).**

If user says "skip all thumbnails" at any point, skip this phase for all remaining entries in the batch.

For each content piece, display:

```
🖼️ Thumbnail/Cover analysis for: "[title]"
```

If YouTube and thumbnail URL was auto-fetched in Phase C:
```
Thumbnail auto-fetched: [thumbnail_url]
```

If any other platform:
```
No auto-fetch available — your answers help track what works.
```

Then ask:

```
1. Text overlay on thumbnail/cover? (yes/no)
   → If yes: What text? ___

2. Face visible? (yes/no)
   → If yes: What emotion? (excited, surprised, frustrated, serious, smiling, other)

3. Visual style? (choose one)
   → clean-minimal, bold-text, before-after, screenshot, face-closeup, listicle, dramatic, other

4. How did this thumbnail perform vs your other content? (choose one)
   → below_average, average, above_average, top_performer, skip
```

### Parsing Rules

- Accept "yes"/"no"/"y"/"n" for boolean questions
- Accept "skip" for any field → leave that thumbnail sub-field null
- If user skips ALL 4 questions → set entire thumbnail to null (don't store empty object)
- Emotion mapping: "happy" → "smiling", "shocked" → "surprised", "angry" → "frustrated"
- Style: exact match from predefined list, or store as "other" if user provides custom input
- "skip all thumbnails" or "skip thumbnails" → skip Phase C.5 for all remaining entries

---

## Phase E: Entry Construction

For each content piece analyzed, build an analytics entry per `schemas/analytics-entry.schema.json`:

```json
{
  "id": "analytics_{YYYYMMDD}_{NNN}",
  "content_id": "[script ID or adhoc ID]",
  "platform": "[platform enum]",
  "published_at": "[ISO 8601]",
  "analyzed_at": "[current ISO 8601]",
  "days_since_publish": "[calculated]",
  "metrics": {
    "views": null,
    "impressions": null,
    "ctr": null,
    "retention_30s": null,
    "avg_view_duration": null,
    "avg_view_percentage": null,
    "completion_rate": null,
    "likes": null,
    "comments": null,
    "shares": null,
    "saves": null,
    "subscribers_gained": null,
    "engagement_rate": null
  },
  "thumbnail": {
    "url": "[YouTube auto-fetched URL or null]",
    "text_overlay": "[from Phase C.5 Q1 or null]",
    "emotion": "[from Phase C.5 Q2 or null]",
    "style": "[from Phase C.5 Q3 or null]",
    "ctr_performance": "[from Phase C.5 Q4 or null]"
  },
  "hook_pattern_used": "[from linked script or null]",
  "topic_category": "[from linked angle/topic or null]",
  "content_pillar": "[from linked angle or null]",
  "is_winner": false,
  "winner_reason": null,
  "collection_method": "[youtube_data_api | user_input | mixed]",
  "source_url": "[URL or null]",
  "notes": null
}
```

### Field Population Rules

- `id`: Generate as `analytics_{YYYYMMDD}_{NNN}` where NNN increments based on existing entries for that date
- `content_id`: Use script ID from scripts.jsonl if linked, otherwise `adhoc_{YYYYMMDD}_{NNN}`
- `days_since_publish`: Calculate from published_at to now
- `engagement_rate`: If not provided by user, calculate: `(likes + comments + shares) / views * 100` (use impressions if views unavailable)
- `collection_method`: `youtube_data_api` if all metrics from API, `user_input` if all manual, `mixed` if combination
- `is_winner`: Always `false` in this plan — winner extraction happens in Plan 05-03
- `hook_pattern_used`: Look up from linked script's hook_ids → hooks.jsonl → pattern field
- `content_pillar`: Look up from linked script's angle_id → angles.jsonl → pillar field
- `thumbnail`: Populate from Phase C.5 responses. For YouTube, set `url` from auto-fetched thumbnail. Set `text_overlay`, `emotion`, `style`, `ctr_performance` from user answers. If ALL thumbnail fields are null/skipped, set entire `thumbnail` to null (omit from entry).

### Null Handling

- Only include metrics the user provided or API returned
- Null/skipped metrics are stored as absent (not included in JSON)
- At least ONE metric must be present per entry (otherwise skip the entry)

---

## Phase F: Persistence & Summary

### Step 1: Save Analytics Entries

Append each constructed entry to `data/analytics/analytics.jsonl` (one JSON object per line).

If the file doesn't exist, create it.

### Step 2: Display Summary

```
════════════════════════════════════════
ANALYSIS COMPLETE
════════════════════════════════════════

┌──────────────────────────┬──────────────┬────────┬──────────┬───────┬────────────┐
│ Content                  │ Platform     │ Views  │ Eng Rate │ CTR   │ Method     │
├──────────────────────────┼──────────────┼────────┼──────────┼───────┼────────────┤
│ [title]                  │ [platform]   │ [N]    │ [N%]     │ [N%]  │ [API/user] │
│ [title]                  │ [platform]   │ [N]    │ [N%]     │ [N%]  │ [API/user] │
└──────────────────────────┴──────────────┴────────┴──────────┴───────┴────────────┘

Entries saved: [N] → data/analytics/analytics.jsonl
Total analyzed (all time): [N]

Notable observations:
- [Any standout metrics — highest views, engagement, etc.]
- [Compare to averages if enough data exists]
```

### Step 2.5: Subscriber / Follower Growth Summary

**Only display if ANY entries in the current batch have `metrics.subscribers_gained` data.**

For YouTube entries with `subscribers_gained`:
```
SUBSCRIBER GROWTH
─────────────────────────────────────────────
Top drivers (this batch):
  #1 "[title]" → +[N] subs
  #2 "[title]" → +[N] subs
  #3 "[title]" → +[N] subs
```

For Instagram entries with `subscribers_gained` (from `followers_gained_attributed`):
```
FOLLOWER GROWTH (attributed)
─────────────────────────────────────────────
Top drivers (this batch):
  #1 "[title]" ([date]) → +[N] followers
  #2 "[title]" ([date]) → +[N] followers
```

**Drop-off alert:** If enough historical data exists (5+ entries with subscriber data for the platform):
- Calculate the average `subscribers_gained` for the last 3 entries vs the prior average
- If last 3 average is < 50% of prior average, display:
```
⚠ Drop-off: Last 3 videos avg +[N] subs (was +[M] prior avg)
```

### Step 3: Feedback Loop Readiness Check

Check `performance_patterns.total_content_analyzed` in agent brain:

- If < 5 total entries: "📊 [N]/5 content pieces analyzed. The feedback loop activates after 5+ entries to ensure reliable patterns."
- If >= 5: "✅ Feedback loop ready. Run winner extraction with a future /viral:analyze --extract-winners to identify patterns and update your brain."

### Step 4: Next Steps

```
────────────────────────────────────────
What's next:
- Run /viral:analyze again after publishing more content
- Recommended: analyze weekly (Fridays) for consistent tracking
- Coming soon: automatic winner extraction + brain updates
────────────────────────────────────────
```

---

## Phase G: Winner Extraction

**Only runs if:** Total entries in `data/analytics/analytics.jsonl` (all time) >= 5.

### Step 1: Check Minimum Data

Read ALL entries from `data/analytics/analytics.jsonl` (not just current batch).

Count total entries. If fewer than 5:
```
📊 Winner extraction needs more data ([N]/5 entries).
   Keep analyzing content — winners activate after 5+ entries!
```
Skip Phase G entirely.

### Step 2: Calculate Platform Baselines

Group ALL historical entries by platform. For each platform with 2+ entries, calculate **median** values for key metrics:

| Platform | Primary Metrics for Baseline |
|----------|------------------------------|
| youtube_longform | median CTR, median avg_view_percentage, median engagement_rate |
| youtube_shorts | median views, median completion_rate, median engagement_rate |
| instagram_reels | median views, median completion_rate, median engagement_rate |
| instagram_posts | median views, median engagement_rate |
| tiktok | median views, median completion_rate, median shares |
| linkedin | median impressions, median engagement_rate, median comments |
| facebook | median views, median engagement_rate |

**Median calculation:** Sort values, take middle value (or average of two middle values for even count). Ignore null/missing values when calculating.

Baselines use ALL historical data, not just the current batch.

### Step 3: Apply Winner Criteria

For EACH entry in the **current batch only** (the entries just saved in Phase F), evaluate against platform-specific thresholds:

| Platform | Winner if ANY of these are true |
|----------|--------------------------------|
| youtube_longform | CTR >= median × 1.5 OR avg_view_percentage >= median × 1.3 OR engagement_rate >= median × 2.0 |
| youtube_shorts | views >= median × 2.0 OR completion_rate >= median × 1.3 |
| instagram_reels | views >= median × 2.0 OR completion_rate >= median × 1.3 |
| instagram_posts | views >= median × 2.0 OR engagement_rate >= median × 1.5 |
| tiktok | views >= median × 2.0 OR shares >= median × 3.0 |
| linkedin | engagement_rate >= median × 1.5 OR comments >= median × 2.0 |
| facebook | views >= median × 2.0 OR engagement_rate >= median × 1.5 |

**Rules:**
- If a metric is null/missing on the entry, skip that criterion (don't penalize missing data)
- If the platform has fewer than 2 historical entries (not enough for baseline), skip winner check for that entry
- A piece needs to exceed ANY ONE threshold to be a winner
- Use the FIRST threshold exceeded as the primary reason

### Step 4: Mark Winners

For each entry in the current batch:

**If winner:**
- Set `is_winner: true`
- Set `winner_reason`: human-readable, e.g., "CTR 8.5% exceeds platform median 4.2% by 2.0x" or "Views 12,400 exceeds platform median 3,100 by 4.0x"
- Set `winner_metrics.threshold_used`: the specific threshold, e.g., "ctr >= median * 1.5"
- Set `winner_metrics.percentile`: calculate where this content ranks among ALL same-platform entries for the triggering metric. Formula: `(count of entries with lower value / total entries) * 100`, rounded to nearest integer.

**If not winner:**
- Keep `is_winner: false`, `winner_reason: null`, `winner_metrics` absent

**Persistence:** Read the full `data/analytics/analytics.jsonl` file, find entries matching the current batch by `id`, update their winner fields, write the entire file back.

### Step 5: Winner Summary Display

Display after the Phase F summary:

```
════════════════════════════════════════
WINNER EXTRACTION (baselines from [N] total entries)
════════════════════════════════════════
```

If winners found:
```
Winners: [N] of [batch size]

🏆 [title] — [platform]
   [winner_reason]

🏆 [title] — [platform]
   [winner_reason]

Did not qualify: [list remaining titles]
```

If no winners:
```
No winners this batch. Your content is tracking near baseline.
Keep publishing — performance data improves pattern detection!
```

```
════════════════════════════════════════
```

---

## Phase G.5: Pattern Report

**Only runs if:** At least 2 entries with `is_winner: true` exist across ALL analytics data (current + historical).

If fewer than 2 winners total:
```
📊 Need more winners for pattern analysis (have [N], need 2+).
   Keep publishing — patterns emerge after multiple wins!
```
Skip Phase G.5.

### Step 1: Aggregate Winner Data

Read ALL entries from `data/analytics/analytics.jsonl`. Separate into two groups:
- **Winners:** entries where `is_winner: true`
- **All entries:** every entry (for calculating win rates)

### Step 2: Analyze Patterns

For each dimension below, count occurrences among winners vs all entries. Calculate **win rate** = (winners with this value / total entries with this value) × 100%.

**Dimensions to analyze:**

1. **Hook Patterns** (`hook_pattern_used`): Count each of the 6 hook patterns among winners vs all. Skip entries where `hook_pattern_used` is null.

2. **Thumbnail Styles** (`thumbnail.style`): Count each style enum among winners vs all. Skip entries where thumbnail or style is null.

3. **Thumbnail Emotions** (`thumbnail.emotion`): Count each emotion enum among winners vs all. Skip entries where thumbnail or emotion is null.

4. **Content Pillars** (`content_pillar`): Count each pillar among winners vs all. Skip entries where `content_pillar` is null.

5. **Platform Win Rates** (`platform`): Count winners per platform vs total entries per platform.

**Only include dimensions that have at least 2 data points** (2+ entries with non-null values for that dimension).

### Step 3: Display Pattern Report

```
════════════════════════════════════════
WINNER PATTERNS (across [N] total winners)
════════════════════════════════════════

🎣 Hook Patterns (win rate):
   [pattern]: [X] wins / [Y] total = [Z]% win rate
   [pattern]: [X] wins / [Y] total = [Z]% win rate
```

If hook data insufficient: `   Not enough hook data yet.`

```
🖼️ Thumbnail Styles (win rate):
   [style]: [X] wins / [Y] total = [Z]% win rate
```

If thumbnail style data insufficient: `   Not enough thumbnail style data yet.`

```
😀 Thumbnail Emotions (win rate):
   [emotion]: [X] wins / [Y] total = [Z]% win rate
```

If thumbnail emotion data insufficient: `   Not enough thumbnail emotion data yet.`

```
📂 Content Pillars (win rate):
   [pillar]: [X] wins / [Y] total = [Z]% win rate
```

If pillar data insufficient: `   Not enough pillar data yet.`

```
📊 Platform Win Rates:
   [platform]: [X] wins / [Y] total = [Z]% win rate
```

```
💡 Key Insight: [Identify highest win-rate value across all dimensions with 2+ data points.
   If a combination stands out (e.g., a hook pattern + thumbnail style both top), mention both.
   Example: "contradiction hooks have 75% win rate — your strongest pattern"
   Example: "face-closeup thumbnails + contradiction hooks dominate with 80%+ win rate"]
════════════════════════════════════════
```

**Sort** each category by win rate descending.
**Key Insight** generation: Find the single dimension value with the highest win rate (minimum 2 data points). If two dimensions both have 60%+ win rate, combine them into a combo insight.

---

## Phase G.6: Top 10 Ranking + Deep Analysis

**Two entry points:**
- **Account Scan Mode:** Called directly from Phase B Step 4 (top 10 table already displayed — skip Steps 1 and 2, go straight to Step 3).
- **Targeted Mode:** Called after Phase G.5 — run Steps 1 and 2 first to build the ranked list from `analytics.jsonl`.

### Step 1: Build the All-Time Top 10 List (Targeted Mode Only)

Read ALL entries from `data/analytics/analytics.jsonl`. Filter to `is_winner: true`.

If fewer than 1 winner total: skip Phase G.6.

For all winners, calculate a **composite score** to rank them:
- Score = `(views / platform_median_views) * 0.4 + (engagement_rate / platform_median_engagement) * 0.35 + (subscribers_gained / platform_median_subs) * 0.25`
- Skip any component where the metric is null (normalize weight across remaining components)
- Sort descending by composite score, take top 10

### Step 2: Display Ranked Table (Targeted Mode Only)

```
════════════════════════════════════════
🏆 TOP 10 WINNING CONTENT (all time)
════════════════════════════════════════

 #  │ Title                              │ Platform          │ Views   │ Eng%  │ Subs+ │ Link
────┼────────────────────────────────────┼───────────────────┼─────────┼───────┼───────┼──────────────────────────
 1  │ [title]                            │ [platform]        │ [N]     │ [N%]  │ [N]   │ [source_url or "no url"]
 2  │ [title]                            │ [platform]        │ [N]     │ [N%]  │ [N]   │ [source_url or "no url"]
...
10  │ [title]                            │ [platform]        │ [N]     │ [N%]  │ [N]   │ [source_url or "no url"]

════════════════════════════════════════
```

- If `source_url` is null for an entry, show "no url"
- Show actual URL (full link, clickable in terminal) — not shortened

### Step 3: Dissect These Top Performers?

Ask one combined question (whether in account scan mode or targeted mode):

```
────────────────────────────────────────
Want to dissect these top performers?

  [3] Top 3  — transcript + visual hook analysis
  [5] Top 5  — transcript + visual hook analysis
  [10] All 10 — transcript + visual hook analysis
  [M] Manual — I'll review the links myself

→
```

Accept `3`, `5`, `10`, "top 3", "top 5", "all", or "m"/"manual". Default to `3` if user just presses Enter.

**If [M] / manual:**
- Display: "Links are above. Run `/viral:analyze --deep-analysis` anytime to run transcript + visual analysis."
- Skip to Phase H.

**If [3] / [5] / [10]:**
- Slice the top 10 list to the chosen count.
- Skip any entries where `source_url` is null (can't download without URL) — log skipped items.
- Display: `"Analyzing [N] pieces — this may take a few minutes..."`
- Proceed to Step 4.

### Step 4: Transcript + Visual Analysis

For each selected winner, run the same analysis as `/viral:discover` Step 4 + Step 5:

**For YouTube (longform or shorts):**

```bash
# Extract video ID from source_url
VIDEO_ID=$(echo "[source_url]" | sed 's/.*[?&]v=\([^&]*\).*/\1/; s|.*/shorts/\([^?]*\).*|\1|')

# Attempt 1: download with ffmpeg time limit (fastest)
yt-dlp --download-sections "*0-60" \
  -f "bestvideo[ext=mp4][height<=720]/bestvideo[height<=720]/best[height<=720]" \
  -o "/tmp/vc_winner_${VIDEO_ID}.%(ext)s" \
  "[source_url]" 2>/tmp/yt_err_${VIDEO_ID}.txt

# If Attempt 1 fails (JS challenge / bot detection), retry without format filter
if [ $? -ne 0 ]; then
  yt-dlp --download-sections "*0-60" \
    -f "best" \
    --no-check-certificates \
    -o "/tmp/vc_winner_${VIDEO_ID}.%(ext)s" \
    "[source_url]" 2>>/tmp/yt_err_${VIDEO_ID}.txt
fi

# Find the downloaded file (extension may vary)
VID_FILE=$(ls /tmp/vc_winner_${VIDEO_ID}.* 2>/dev/null | grep -v ".txt" | head -1)

# Extract frames (1 per second, max 20 frames for longform / 15 for shorts)
if [ -n "$VID_FILE" ]; then
  FRAMES=$([ "${FORMAT}" = "youtube_longform" ] && echo 20 || echo 15)
  ffmpeg -i "$VID_FILE" \
    -vf "fps=1,scale=640:-1" \
    -frames:v $FRAMES \
    "/tmp/vc_winner_${VIDEO_ID}_frame_%03d.jpg" -y 2>/dev/null
else
  echo "DOWNLOAD_FAILED: $(cat /tmp/yt_err_${VIDEO_ID}.txt | tail -3)"
fi
```

Then read the frames via the Read tool (as images) and analyze them.

**For Instagram Reels:**

If `source_url` is an Instagram URL, use the instaloader Python API (more reliable than yt-dlp for Instagram):

```python
python3 - <<'EOF'
import instaloader, os, sys

SHORTCODE = sys.argv[1]  # extracted from source_url
L = instaloader.Instaloader(download_pictures=False, download_video_thumbnails=False,
                              post_metadata_txt_pattern='', dirname_pattern='/tmp/vc_ig_{profile}')
try:
    post = instaloader.Post.from_shortcode(L.context, SHORTCODE)
    L.download_post(post, target=f'/tmp/vc_ig_{SHORTCODE}')
    print('OK')
except Exception as e:
    print(f'FAILED: {e}')
EOF
```

Then find the `.mp4` file in `/tmp/vc_ig_{SHORTCODE}/` and extract frames with ffmpeg (15 frames, 1/sec).

If instaloader fails, fall back to yt-dlp:
```bash
yt-dlp -f "best[ext=mp4]/best" -o "/tmp/vc_winner_ig_${SHORTCODE}.%(ext)s" "[source_url]"
```

**If download fails for any piece:** Log title + error reason, mark as `download_failed`, continue to the next. Show all failures in the summary.

### Step 4b: Display Deep Analysis Per Winner

For each winner analyzed, display:

```
────────────────────────────────────────
🏆 #[rank]: [title]
Platform: [platform] | Published: [date] | Views: [N] | Eng: [N%]
Link: [source_url]
────────────────────────────────────────

VERBAL HOOK (first 3-5 seconds):
  Opening line: "[exact words spoken]"
  Hook pattern: [contradiction / specificity / timeframe_tension / etc.]
  Hook strength: [weak / moderate / strong / excellent]
  Why it works: [1 sentence]

VISUAL HOOK (first 3 seconds on screen):
  On screen: [what's shown — person, text, graphic, action]
  Text overlays: [any text visible in first 3s or "none"]
  Visual type: [talking-head / screen-recording / b-roll / text-only / etc.]
  Pattern interrupt: [yes — describe / no]
  Pacing: [slow / medium / fast / cut-heavy]

WHAT'S SHOWN (0:03–0:20):
  [description of the visual content — what draws attention, what's happening]

WHY THIS WON:
  [1-2 sentences connecting the hook/visual style to the performance metrics]
  Proof: [N] views / [N%] engagement / +[N] subs
```

### Step 5: Winner Analysis Summary

After all pieces are analyzed, display:

```
════════════════════════════════════════
WINNER ANALYSIS COMPLETE
════════════════════════════════════════

Analyzed: [N] of [N selected]
Failed:   [N] (listed below if any)

COMMON PATTERNS IN YOUR TOP CONTENT:
  Hook patterns: [most common across winners]
  Visual type:   [most common]
  Pattern interrupt: [% that used one]
  Opening style: [observation about what winners open with]

APPLY TO YOUR NEXT VIDEO:
  → [1 specific hook recommendation based on what's winning]
  → [1 specific visual/pacing recommendation]

Failed downloads: [list titles + reason, or "none"]

────────────────────────────────────────
Next step: Run /viral:update-brain to push these patterns
into your agent brain so future content uses what's winning.
────────────────────────────────────────
════════════════════════════════════════
```

After displaying, skip to Phase H.

---

## Phase H: Feedback Loop

**Runs after Phase G.5.** Auto-updates the hook repository and agent brain based on winner data.

### Step 1: Minimum Data Check

If fewer than 5 total entries in `data/analytics/analytics.jsonl`:
```
🧠 Feedback loop needs more data ([N]/5 entries).
   Brain updates activate after 5+ entries. Keep analyzing!
```
Skip Phase H entirely.

If 5+ entries: proceed.

### Step 2: Update Hook Repository

For each entry in the CURRENT batch that has:
- Non-null `hook_pattern_used`
- `content_id` starting with `script_` (not adhoc content)

Do:
1. Look up the script in `data/scripts.jsonl` by `content_id`
2. From the script, get `hook_ids` array
3. For each hook_id, find matching hook in `data/hooks.jsonl`
4. Apply status update:

| Condition | New Status | Action |
|-----------|-----------|--------|
| Entry `is_winner: true` | `winner` | Set status → "winner", populate `performance` object (ctr, retention_30s, engagement_rate, analyzed_at) |
| Entry `is_winner: false` AND `days_since_publish` >= 7 | `dud` | Set status → "dud", populate `performance` with available metrics |
| Entry `is_winner: false` AND `days_since_publish` < 7 | `used` (if currently draft/approved) | Too early to judge — mark as used but don't declare dud |

5. Write updated hooks back to `data/hooks.jsonl`
6. Display: `"Hooks updated: [N] winners, [N] duds, [N] too early"`

**Rules:**
- Only update hooks that actually exist in hooks.jsonl (skip if not found)
- If a hook already has status "winner", don't downgrade it
- Performance data overwrites previous performance (latest analysis wins)

### Step 3: Update Agent Brain

Read `data/agent-brain.json`. Update these sections:

**A. hook_preferences** (pattern scoring adjustments):

For each of the 6 hook patterns:
1. Count wins: entries in ALL analytics where `is_winner: true` AND `hook_pattern_used` matches
2. Count total uses: ALL analytics entries where `hook_pattern_used` matches
3. Calculate win rate = wins / total
4. Apply adjustment:
   - Win rate >= 50% → add +0.5 to current preference value
   - Win rate > 0% and < 50% → no change
   - Win rate == 0% AND total uses >= 3 → add -0.2
5. Clamp all values to [-2.0, 5.0]
6. Only update patterns with 2+ total uses (skip patterns with 0-1 uses)

**B. learning_weights** (topic/pillar scoring):

For each unique `content_pillar` in ALL analytics:
1. Calculate pillar win rate = pillar winners / pillar total
2. If win rate >= 50% → add +0.1 to `icp_relevance` weight
3. Clamp `icp_relevance` to [0.5, 2.0]
4. Only adjust for pillars with 2+ entries

Note: learning_weights are global in v0.1. Winning pillars boost `icp_relevance` since they validate ICP alignment.

**C. performance_patterns:**

Update with running aggregates from ALL analytics data:
- `total_content_analyzed`: total entry count
- `avg_ctr`: average of all non-null `metrics.ctr` values (round to 1 decimal)
- `avg_retention_30s`: average of all non-null `metrics.retention_30s` values (round to 1 decimal)
- `top_performing_topics`: top 5 `topic_category` values by win rate (minimum 2 entries each), as array of strings
- `top_performing_formats`: top 3 `platform` values by win rate (minimum 2 entries each), as array of strings
- `audience_growth_drivers`: top 3 `topic_category` values by total `subscribers_gained`, as array of strings (empty if no subscriber data)

**D. metadata:**

- Set `metadata.updated_at` to current ISO 8601 timestamp
- Append to `metadata.evolution_log`:
  ```json
  {
    "timestamp": "[current ISO 8601]",
    "reason": "Auto-update via /viral:analyze feedback loop",
    "changes": [
      "hook_preferences: [list changes, e.g., 'contradiction +0.5 (67% win rate)']",
      "performance_patterns: [N] total analyzed, avg CTR [X]%",
      "other notable changes..."
    ]
  }
  ```

Write updated brain back to `data/agent-brain.json`.

### Step 4: Feedback Summary

Display:
```
════════════════════════════════════════
FEEDBACK LOOP
════════════════════════════════════════

🎣 Hook Updates:
   Winners: [N] | Duds: [N] | Too early: [N]

🧠 Brain Updates:
   hook_preferences: [list changes or "no adjustment needed"]
   learning_weights: [changes or "no adjustment needed"]
   performance_patterns: [N] total analyzed, avg CTR [X]%

📊 Running Averages:
   CTR: [X]% | 30s Retention: [X]% | Content Analyzed: [N]

🔄 Evolution logged to agent-brain.json
════════════════════════════════════════
```

If no hooks were linked (all adhoc content or no hook data):
```
🎣 No hooks to update (content not linked to hook repository)
```

If no brain changes were needed (all patterns neutral):
```
🧠 Brain stable — no preference adjustments triggered
   (Changes require 50%+ win rate for boosts, 0% with 3+ uses for penalties)
```

---

## Automation & Cron

### Weekly Cron (Friday 1 AM EST)

The analysis pipeline can run automatically via `scripts/weekly-analyze.sh`:

```bash
# Manual run
./scripts/weekly-analyze.sh

# Dry run (see what would happen without executing)
./scripts/weekly-analyze.sh --dry-run
```

**Schedule:** Friday 06:00 UTC (1:00 AM EST) via macOS launchd.

**Install launchd plist:**
```bash
# Edit the plist to set your content-pipeline path, then:
cp com.viralcommand.weekly-analyze.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.viralcommand.weekly-analyze.plist
```

The cron script invokes `claude -p "/viral:analyze --manual --all"` which runs the full pipeline (Phases A-H) non-interactively. Only platforms with API access (YouTube) collect new data automatically — platforms requiring interactive input are skipped in manual mode.

### Manual Trigger

Run a full analysis cycle manually at any time:
```
/viral:analyze --manual --all
```

Or target a specific platform:
```
/viral:analyze --manual --youtube
```

### Companion Cron

- **Daily discovery:** `scripts/daily-discover.sh` — competitor scraping + topic scoring (daily 6 AM)
- **Weekly analysis:** `scripts/weekly-analyze.sh` — performance analytics + feedback loop (Friday 1 AM EST)

Together these two crons form the automated learning cycle: discover → create → analyze → learn → repeat.

---

## Important Rules

1. **NEVER fabricate metrics** — only use YouTube Data API responses or user-provided data. If you can't verify a number, don't include it.
2. **ALWAYS accept "skip"** for any metric. Partial data is better than no data.
3. **Parse fuzzy numbers** — users will type "5k", "~800", "2.3M". Convert to integers.
4. **YouTube Data API key** comes from `.env` file as `YOUTUBE_DATA_API_KEY`, not from agent-brain.json. The brain's `api_keys_configured` array only tracks WHICH APIs are set up.
5. **YouTube Analytics API** requires OAuth — run `python scripts/setup-yt-oauth.py` first. If token exists at `~/.viral-command/yt-token.json`, use `scripts/fetch-yt-analytics.py` for rich metrics (avg view duration, subs gained, watch time). CTR is NOT available via any API — always ask user for CTR.
6. **Validate ranges** — CTR 0-100%, views >= 0, etc. Ask for confirmation if values seem wrong.
7. **One entry per content piece per analysis run** — don't merge with previous entries. Multiple entries for the same content show performance over time.
8. **is_winner is determined by Phase G** winner extraction using median-based platform-specific thresholds. Minimum 5 total analytics entries required before extraction activates. Multipliers are hardcoded for v0.1.
9. **Phase H updates agent-brain.json** (hook_preferences, learning_weights, performance_patterns, evolution_log) **and hooks.jsonl** (status, performance). These updates require 5+ total analytics entries. Updates are additive — they adjust existing values, never reset them.
10. **Ad-hoc content welcome** — users can analyze content not generated by /viral:script. Generate adhoc_ IDs for these.
11. **Thumbnail questions are optional** — if user says "skip all thumbnails" during a batch, skip Phase C.5 for all remaining entries. Partial thumbnail data is fine (e.g., only style + ctr_performance).
