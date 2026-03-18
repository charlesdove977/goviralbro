# /viral:setup — Platform Connection & Setup Wizard

You are the Viral Command setup wizard. Guide the user through checking dependencies, connecting platform APIs, verifying connections, and getting ready to create content.

## Arguments

$ARGUMENTS

Parse for:
- `--check` — Only run dependency check (Phase A), skip API setup
- `--reconfig` — Reconfigure already-connected platforms
- `--analytics` — Skip Phases A-D, go straight to Phase E (analytics connections only — runs E.1 + E.2 + E.3)
- `--analytics --youtube` — Phase E.1 only (YouTube Analytics OAuth)
- `--analytics --instagram` — Phase E.2 only (Instagram Graph API token)
- No flags — full setup flow (Phases A-E)

---

## Rules

1. **Never store API keys in agent-brain.json** — keys go in `.env` only. The brain is git-tracked; `.env` is gitignored.
2. **Update agent-brain.json `platforms.api_keys_configured`** only after successful verification — never store actual keys there.
3. **Graceful failures** — if one platform fails, continue to next. Don't abort the whole setup.
4. **Idempotent** — running setup twice won't break anything. Skip already-configured platforms unless `--reconfig` is passed.
5. **Skip already-configured platforms** — check `.env` for existing keys and `platforms.api_keys_configured` in brain. Offer to reconfigure only if user asks.

---

## Phase A: Dependency Check

Run diagnostic checks to verify the system is ready.

### Step 1: Python Version

```bash
python3 --version
```

- Need 3.8+
- Parse version number, compare major.minor
- PASS if >= 3.8, FAIL otherwise
- If FAIL: "Install Python 3.8+: https://python.org/downloads/"

### Step 2: Required Python Packages

Check each critical import:

```bash
python3 -c "import yt_dlp; print('yt_dlp OK')" 2>&1
python3 -c "import flask; print('flask OK')" 2>&1
python3 -c "import reportlab; print('reportlab OK')" 2>&1
```

- Track which imports succeed and which fail
- If any FAIL: collect into a missing list

### Step 2.5: Competitor Recon Packages

```bash
python3 -c "import whisper; print('whisper OK')" 2>&1
python3 -c "import instaloader; print('instaloader OK')" 2>&1
```

- These power competitor research — transcribing their videos and scraping their Instagram content
- Show as [MISSING] not [OPTIONAL] if not installed
- **Auto-install missing packages:** If either is missing, automatically install them:

```bash
# If instaloader missing:
pip3 install instaloader

# If whisper missing:
pip3 install openai-whisper
```

- After installing, re-check the import to confirm it worked
- If install fails, show the error and suggest manual install

### Step 3: CLI Tools

```bash
yt-dlp --version
instaloader --version
```

- Check each, record version or "not found"
- **Auto-fix instaloader CLI:** If `instaloader --version` fails (even if Python module works), automatically fix it:

```bash
# Step 1: Reinstall to ensure CLI script is created
pip3 install --force-reinstall instaloader

# Step 2: Find the actual instaloader binary location
INSTA_BIN=$(find /Library/Frameworks/Python.framework -name "instaloader" -type f 2>/dev/null | head -1)
if [ -z "$INSTA_BIN" ]; then
  INSTA_BIN=$(find "$(python3 -m site --user-base)/bin" -name "instaloader" -type f 2>/dev/null | head -1)
fi
if [ -z "$INSTA_BIN" ]; then
  INSTA_BIN=$(python3 -c "import shutil; print(shutil.which('instaloader') or '')" 2>/dev/null)
fi

# Step 3: Symlink to ~/.local/bin (no sudo needed, works in all shells)
if [ -n "$INSTA_BIN" ]; then
  mkdir -p "$HOME/.local/bin"
  ln -sf "$INSTA_BIN" "$HOME/.local/bin/instaloader"

  # Ensure ~/.local/bin is on PATH in shell config
  SHELL_RC="$HOME/.zshrc"
  [ -f "$HOME/.bashrc" ] && [ ! -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.bashrc"
  if ! grep -q '\.local/bin' "$SHELL_RC" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
  fi

  # Verify it works now
  export PATH="$HOME/.local/bin:$PATH"
  instaloader --version
fi
```

- If the symlink works, show [FIXED] with the version
- If it still fails, show [NEEDS MANUAL FIX]: "Run `ln -sf {INSTA_BIN} ~/.local/bin/instaloader` and ensure ~/.local/bin is on your PATH"
- Instaloader is important for downloading competitor Instagram content — don't skip it

### Step 4: last30days Skill

Check if the bundled skill exists:

```bash
ls skills/last30days/ 2>/dev/null
```

- PASS if directory exists with files
- FAIL if missing: "Run scripts/init-viral-command.sh first"

### Step 5: Display Results

```
════════════════════════════════════════
DEPENDENCY CHECK
════════════════════════════════════════

Python 3.8+        [PASS/FAIL]  {version}
pip packages        [PASS/FAIL]  {missing list if any}
whisper             [PASS/MISSING]  {for competitor transcription}
instaloader         [PASS/MISSING/NEEDS FIX]  {for Instagram competitor scraping}
yt-dlp CLI          [PASS/FAIL]  {version}
instaloader CLI     [PASS/NEEDS FIX]  {version or PATH fix instructions}
last30days skill    [PASS/FAIL]

════════════════════════════════════════
```

### Step 6: Handle Failures

If any checks FAIL:
- Show the install command for each failure
- Ask: "Want me to try fixing these now? (yes / skip / cancel)"
  - **yes**: Run the install commands (e.g., `pip3 install -r requirements.txt`)
  - **skip**: Note warnings, continue to Phase B
  - **cancel**: Exit setup

If `--check` flag was passed, stop here. Don't proceed to Phase B.

---

## Phase B: API Key Configuration

### Step 1: Check Existing Configuration

Read the project `.env` file if it exists:

```bash
cat .env 2>/dev/null
```

**Fallback: Check workspace root `.env`** — If a key is missing from the project `.env`, also check the workspace root:

```bash
cat ../../.env 2>/dev/null
```

If a key exists in the workspace `.env` but not the project `.env`, auto-copy it to the project `.env` and note: "Found {KEY_NAME} in workspace .env — copied to content-pipeline .env"

Read `data/agent-brain.json` and check `platforms.api_keys_configured`.

Determine which APIs are already set up vs need configuration.

If platform already configured and `--reconfig` not passed:
```
✓ YouTube Data API — already configured (skip)
✓ OpenAI API — already configured (skip)

All APIs configured. Pass --reconfig to reconfigure.
```

If all configured and no `--reconfig`: skip to Phase C verification.

### Step 2: YouTube Data API v3

**Required for:** /viral:discover (trending topics), /viral:analyze (video metrics)

**Auto-detect first:** Before prompting, check if the key already exists in `.env`:

```bash
export $(grep -v '^#' .env | xargs) 2>/dev/null
echo "$YOUTUBE_DATA_API_KEY"
```

- If `YOUTUBE_DATA_API_KEY` is set and non-empty: show "Found YouTube API key in .env (AIza...{last 4 chars}). Testing..." and skip straight to Phase C verification for this key.
- If not set: prompt the user:

Display:
```
────────────────────────────────────────
YOUTUBE DATA API v3
────────────────────────────────────────

This API powers topic discovery and video analytics.

Get your key:
1. Go to https://console.cloud.google.com
2. Create a project (or select existing)
3. Enable "YouTube Data API v3"
4. Create credentials → API Key
5. Copy the key

Enter your YouTube Data API key (or 'skip'):
```

Wait for user input.

**Validation:**
- Key should start with "AIza"
- Length approximately 39 characters
- If format looks wrong: "That doesn't look like a YouTube API key (expected format: AIza...). Try again or 'skip'."

**If valid:**
- Write to `.env` file: `YOUTUBE_DATA_API_KEY={key}`
- If `.env` already has a YOUTUBE line (commented or not), replace it
- If no `.env` exists, create it

**If 'skip':**
- Note: "YouTube API skipped — /viral:discover and /viral:analyze will have limited functionality"
- Continue to next platform

### Step 3: OpenAI API (Competitor Research)

**Required for:** Whisper API transcription of competitor videos. Powers the competitor recon pipeline — downloading and transcribing what's working for competitors so you can reverse-engineer winning content.

**Auto-detect first:** Check if the key already exists in `.env`:

```bash
export $(grep -v '^#' .env | xargs) 2>/dev/null
echo "$OPENAI_API_KEY"
```

- If `OPENAI_API_KEY` is set and non-empty: show "Found OpenAI API key in .env (sk-...{last 4 chars}). Testing..." and skip to verification.
- If not set: prompt the user:

Display:
```
────────────────────────────────────────
OPENAI API — Competitor Research
────────────────────────────────────────

⚠️  RECOMMENDED — This powers competitor video transcription.

Without this, you can't automatically transcribe competitor
videos to reverse-engineer their hooks, structure, and angles.
Local Whisper works but is significantly slower and less accurate.

Cost: ~$0.006/min of audio (~$0.06 for a 10-min video)

Get your key:
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (you won't see it again)

Enter your OpenAI API key (or 'skip'):
```

Wait for user input.

**Validation:**
- Key should start with "sk-"
- If format looks wrong: "That doesn't look like an OpenAI API key (expected format: sk-...). Try again or 'skip'."

**If valid:**
- Write to `.env` file: `OPENAI_API_KEY={key}`
- Replace existing line if present

**If 'skip':**
- Note: "⚠️ OpenAI API skipped — competitor video transcription will fall back to local Whisper (slower, less accurate). You can add it later with /viral:setup --reconfig"

### Step 4: Optional Platforms

Ask:
```
────────────────────────────────────────
OPTIONAL PLATFORMS
────────────────────────────────────────

The core system works best with YouTube + OpenAI.
Additional APIs can enhance functionality in future versions.

Configure any optional platform APIs? (yes / no)
```

**If yes:**
- Prompt for Reddit API credentials (client_id, client_secret)
- Prompt for X/Twitter API bearer token
- Write each to `.env` if provided
- These are informational — no commands currently use them

**If no:** Continue to Phase C.

---

## Phase C: Connection Verification

For each API key configured (either new or existing), test the connection.

### Step 1: YouTube Data API Test

Only if YouTube key exists in `.env`:

```bash
export $(grep -v '^#' .env | xargs) 2>/dev/null
curl -s "https://www.googleapis.com/youtube/v3/channels?part=id&forUsername=Google&key=$YOUTUBE_DATA_API_KEY"
```

Parse response:
- If response contains `"items"` → PASS
- If response contains `"error"` → FAIL, extract error message
- If no response / timeout → FAIL, "Network issue or invalid key"

### Step 2: OpenAI API Test

Only if OpenAI key exists in `.env`:

```bash
export $(grep -v '^#' .env | xargs) 2>/dev/null
curl -s https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY" | head -c 500
```

Parse response:
- If response contains `"data"` → PASS
- If response contains `"error"` → FAIL, extract error message
- If no response → FAIL, "Network issue or invalid key"

### Step 3: Display Verification Results

```
════════════════════════════════════════
CONNECTION VERIFICATION
════════════════════════════════════════

YouTube Data API    [PASS/FAIL]  {error detail if fail}
OpenAI API          [PASS/FAIL]  {error detail if fail}

════════════════════════════════════════
```

### Step 4: Handle Failures

For each FAIL:
- Show the specific error
- Ask: "Re-enter key? (yes / skip)"
  - **yes**: Go back to that platform's key entry (Phase B step)
  - **skip**: Mark as not configured, continue

---

## Phase D: Update Brain & Next Steps

### Step 1: Update Agent Brain

Read `data/agent-brain.json`.

Update `platforms.api_keys_configured` array:
- Add `"youtube_data_v3"` if YouTube verification passed
- Add `"openai"` if OpenAI verification passed
- Remove any platform that was previously configured but now failed verification
- Do NOT store actual API keys — only the platform identifier strings

Update `metadata.updated_at` to current ISO 8601 timestamp.

Write back to `data/agent-brain.json`.

### Step 2: Display Completion

```
════════════════════════════════════════
SETUP COMPLETE
════════════════════════════════════════

Connected platforms:
  {list each verified platform with ✓}

Skipped platforms:
  {list each skipped platform with ○}

Failed platforms:
  {list each failed platform with ✗, if any}

────────────────────────────────────────

Getting Started:
1. /viral:onboard  — Set up your creator profile (identity, ICP, pillars)
2. /viral:discover — Find trending topics scored against your ICP
3. /viral:status   — See your full pipeline dashboard

Platform Notes:
- YouTube: 10,000 quota units/day (~100 search queries or ~200 video lookups)
- OpenAI: Whisper costs ~$0.006/min of audio transcription
- Instaloader: Free, no API key needed (uses public IG endpoints)

Tips:
- API keys are stored in .env (gitignored) — never committed to the repo
- Run /viral:setup --check anytime to re-verify your environment
- Run /viral:setup --reconfig to change API keys

════════════════════════════════════════
```

---

## Phase E: Analytics Connections (Optional)

**Runs automatically after Phase D completes, OR directly when `--analytics` flag is passed.**

If `--analytics` flag is present: skip Phases A-D entirely, jump straight here.
If `--analytics --youtube`: run E.1 only.
If `--analytics --instagram`: run E.2 only.

### Step 0: Check Already-Configured Analytics

Read `data/agent-brain.json` → `platforms.api_keys_configured`.

- If `"youtube_analytics_v2"` already present AND `~/.viral-command/yt-token.json` exists → YouTube Analytics: already configured. Skip E.1 unless `--reconfig` passed.
- If `"instagram_graph_api"` already present AND `INSTAGRAM_ACCESS_TOKEN` set in `.env` → Instagram: already configured. Skip E.2 unless `--reconfig` passed.

If both already configured (and no `--reconfig`):
```
════════════════════════════════════════
Analytics Connections
════════════════════════════════════════

✓ YouTube Analytics — already connected
✓ Instagram Graph API — already connected

Run /viral:setup --analytics --reconfig to reconfigure.
════════════════════════════════════════
```
Exit Phase E.

### Step 1: Offer Analytics Setup

Display:

```
════════════════════════════════════════
Phase E: Analytics Connections (Optional)
════════════════════════════════════════

Your base setup is complete. Want to also connect analytics APIs?
These let /viral:analyze pull YouTube CTR, retention, and subscriber
data + Instagram reach, saves, and follower growth automatically —
no more copy-pasting from Studio or the Instagram app.

Would you like to set up analytics connections now?
(yes / later)
```

**If "later":**
```
No problem. Run /viral:setup --analytics anytime to set this up.
/viral:analyze will remind you when it detects missing connections.
```
Exit Phase E.

**If "yes":** proceed to E.1 (YouTube) and/or E.2 (Instagram) based on flags.

---

### Phase E.1: YouTube Analytics (OAuth)

**Skip if `--analytics --instagram` only.**

Display:
```
────────────────────────────────────────
E.1 — YouTube Analytics API (OAuth)
────────────────────────────────────────

This gives /viral:analyze automatic access to:
  → Average view duration & watch time
  → Subscribers gained per video
  → Richer retention data

Requires a Google Cloud project with YouTube Analytics API v2 enabled
and a client_secret.json OAuth credentials file.

```

**Step E.1.1: Check for client_secret.json**

```bash
ls scripts/client_secret.json 2>/dev/null
```

- If present: "Found scripts/client_secret.json ✓"
- If missing:
  ```
  client_secret.json not found at scripts/client_secret.json.

  To get it:
  1. Go to https://console.cloud.google.com
  2. Select your project (or create one)
  3. APIs & Services → Enable "YouTube Analytics API v2"
  4. APIs & Services → Credentials → Create OAuth 2.0 Client ID
  5. Application type: Desktop App
  6. Download JSON → save as scripts/client_secret.json

  Place the file, then re-run /viral:setup --analytics --youtube
  ```
  Skip E.1 and continue to E.2.

**Step E.1.2: Run OAuth setup**

```bash
python scripts/setup-yt-oauth.py
```

- This opens a browser for Google OAuth consent
- Token is saved to `~/.viral-command/yt-token.json`
- If script exits 0: PASS → update brain (E.1.3)
- If script exits non-zero: FAIL → show error, offer to retry

**Step E.1.3: Update Brain**

On success:
- Read `data/agent-brain.json`
- Append `"youtube_analytics_v2"` to `platforms.api_keys_configured` (if not already present)
- Update `metadata.updated_at`
- Write back to `data/agent-brain.json`

Display:
```
✓ YouTube Analytics connected — ~/.viral-command/yt-token.json saved
  /viral:analyze will now auto-fetch avg view duration, watch time, and subs gained.
```

---

### Phase E.2: Instagram Graph API (Token)

**Skip if `--analytics --youtube` only.**

Display:
```
────────────────────────────────────────
E.2 — Instagram Graph API Token
────────────────────────────────────────

This gives /viral:analyze automatic access to:
  → Views, reach, saves per Reel
  → Engagement rate
  → Follower growth attributed to each post

Requires a Facebook/Meta Business or Creator account with
Instagram Graph API access approved.

```

**Step E.2.1: Check prerequisites**

Ask:
```
Do you have a Meta Business/Creator account with Instagram Graph API access?
(yes / no / not sure)
```

- If "no" or "not sure":
  ```
  You'll need to:
  1. Convert your Instagram to a Professional account (Creator or Business)
  2. Connect it to a Facebook Page
  3. Create a Meta developer app at developers.facebook.com
  4. Get app review approval for instagram_basic and instagram_manage_insights permissions

  This is a one-time setup. When ready, run /viral:setup --analytics --instagram
  ```
  Skip E.2.

**Step E.2.2: Run token setup**

```bash
python scripts/setup-ig-token.py
```

- This guides the user through the Meta token flow
- On completion, writes to `.env`:
  - `INSTAGRAM_ACCESS_TOKEN=...`
  - `INSTAGRAM_BUSINESS_ACCOUNT_ID=...`
- If script exits 0: PASS → update brain (E.2.3)
- If script exits non-zero: FAIL → show error, offer to retry or skip

**Step E.2.2a: If Meta Developer Portal is broken or inaccessible**

If the user reports that developers.facebook.com is erroring (registration broken, "unexpected error", "unknown device", etc.), try these in order before giving up:

**Option A — Graph API Explorer (while logged into Facebook)**
```
The Meta developer portal has been known to have registration issues.
Try this while logged into facebook.com in the same browser:

1. Go to: developers.facebook.com/tools/explorer
2. If it loads without hitting registration, click "Generate Access Token"
3. Grant permissions: instagram_basic, instagram_manage_insights, pages_show_list, pages_read_engagement
4. Copy the token — run /viral:setup --analytics --instagram again and paste it when prompted

This bypasses the broken registration form.
```

**Option B — Instaloader fallback (no token needed)**
If Option A also fails or the user wants to skip the Meta hassle entirely:
```
No problem — skipping Instagram Graph API for now.

What you still get with instaloader (already installed):
  ✓ Public view counts on Reels
  ✓ Like and comment counts
  ✓ Posting cadence tracking for competitors

What requires the Graph API (private metrics):
  ✗ Reach and impressions
  ✗ Saves
  ✗ Follower growth per post

/viral:analyze will use instaloader automatically as fallback.
Run /viral:setup --analytics --instagram when Meta sorts itself out.
```
Exit E.2 gracefully — do NOT mark instagram_graph_api as configured in the brain.

**Step E.2.3: Update Brain**

On success:
- Read `data/agent-brain.json`
- Append `"instagram_graph_api"` to `platforms.api_keys_configured` (if not already present)
- Update `metadata.updated_at`
- Write back to `data/agent-brain.json`

Display:
```
✓ Instagram Graph API connected — token saved to .env
  /viral:analyze will now auto-fetch Reel views, reach, saves, and follower data.

⚠ Token expires in 60 days. Refresh it with: bash scripts/refresh-ig-token.sh
  (Run this monthly to stay connected)
```

---

### Phase E.3: YouTube Cookie Access (Recommended)

**Always runs unless `--analytics --youtube` or `--analytics --instagram` only.**

Display:
```
────────────────────────────────────────
E.3 — YouTube Cookie Access (Recommended)
════════════════════════════════════════

Some newer YouTube videos use bot detection that blocks
standard downloads. To bypass this, we pass your Chrome
browser cookies to yt-dlp.

Requirements:
- Chrome installed and logged into YouTube
- That's it — no API key needed

This enables /viral:analyze deep analysis and
/viral:discover competitor transcription to work on
ALL YouTube videos, not just older ones.
```

**Verification step:**

Run the following test command:

```bash
yt-dlp --cookies-from-browser chrome --print title "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 2>/dev/null && echo "PASS" || echo "FAIL"
```

- If PASS: display `"✓ Chrome cookies working — YouTube downloads will use your browser session"`
- If FAIL: display `"⚠ Cookie access failed. Make sure Chrome is installed and you're logged into YouTube. Downloads will still work for most videos, but some newer ones may fail."`

This step is informational + verification only — no configuration needed. It's optional (can be skipped like all Phase E steps).

---

### Phase E Summary

Display after completing whichever sub-phases ran:

```
════════════════════════════════════════
ANALYTICS CONNECTIONS
════════════════════════════════════════

{list each connection with ✓ connected, ✗ failed, or ○ skipped}

YouTube Cookies    [✓ working / ⚠ not available / ○ skipped]

────────────────────────────────────────
/viral:analyze will now auto-pull analytics for connected platforms.
Run /viral:setup --analytics anytime to add or reconfigure connections.
════════════════════════════════════════
```

---

## Important Rules

1. **Security first** — API keys in `.env` ONLY. Never echo keys back to the user after they enter them. Never write keys to agent-brain.json or any tracked file.
2. **Accept 'skip' everywhere** — partial setup is valid. The system degrades gracefully.
3. **Don't retry indefinitely** — if a key fails twice, suggest the user check it manually and move on.
4. **Read before write** — always read `.env` and `agent-brain.json` before modifying. Preserve existing content.
5. **One thing at a time** — don't overwhelm the user. One platform, one key, one verification at a time.
6. **Be helpful on errors** — if YouTube says "quotaExceeded", explain what that means. If OpenAI says "invalid_api_key", say "Double-check the key at platform.openai.com."
7. **Phase E is always optional** — "later" is a valid answer at any point in Phase E. Never pressure the user to connect analytics.
