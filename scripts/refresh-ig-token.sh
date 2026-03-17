#!/usr/bin/env bash
#
# Refresh Instagram long-lived access token.
# Token lasts 60 days — run this every 50 days to stay valid.
#
# Schedule via cron or launchd:
#   crontab: 0 6 */50 * * /path/to/scripts/refresh-ig-token.sh
#   launchd: see docs/CRON-SETUP.md
#
# Requires: INSTAGRAM_ACCESS_TOKEN in .env

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/ig-token-refresh.log"

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Load current token from .env
if [ ! -f "$ENV_FILE" ]; then
    log "ERROR: .env not found at $ENV_FILE"
    exit 1
fi

CURRENT_TOKEN=$(grep '^INSTAGRAM_ACCESS_TOKEN=' "$ENV_FILE" | cut -d'=' -f2-)

if [ -z "$CURRENT_TOKEN" ]; then
    log "ERROR: INSTAGRAM_ACCESS_TOKEN not found in .env"
    exit 1
fi

log "Refreshing Instagram token..."

# Call Meta Graph API to refresh
RESPONSE=$(curl -s "https://graph.facebook.com/v21.0/oauth/access_token?grant_type=ig_exchange_token&access_token=$CURRENT_TOKEN")

# Check for error
if echo "$RESPONSE" | grep -q '"error"'; then
    ERROR_MSG=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['error']['message'])" 2>/dev/null || echo "$RESPONSE")
    log "ERROR: Token refresh failed — $ERROR_MSG"
    log "Re-run: python scripts/setup-ig-token.py"
    exit 1
fi

# Extract new token
NEW_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$NEW_TOKEN" ]; then
    log "ERROR: Could not parse new token from response"
    exit 1
fi

# Update .env file (replace old token with new)
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|^INSTAGRAM_ACCESS_TOKEN=.*|INSTAGRAM_ACCESS_TOKEN=$NEW_TOKEN|" "$ENV_FILE"
else
    sed -i "s|^INSTAGRAM_ACCESS_TOKEN=.*|INSTAGRAM_ACCESS_TOKEN=$NEW_TOKEN|" "$ENV_FILE"
fi

EXPIRES_IN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('expires_in', 'unknown'))" 2>/dev/null)
DAYS=$((EXPIRES_IN / 86400))

log "Token refreshed successfully. Expires in ~${DAYS} days."
