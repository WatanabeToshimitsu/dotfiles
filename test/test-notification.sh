#!/usr/bin/env bash
set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$DOTFILES_DIR/claude/hooks/notification.sh"
TEST_ROOT=$(mktemp -d)
FAKE_BIN="$TEST_ROOT/bin"
CURL_LOG="$TEST_ROOT/curl.log"
trap 'rm -rf "$TEST_ROOT"' EXIT

mkdir -p "$FAKE_BIN"
cat > "$FAKE_BIN/curl" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$CURL_LOG"
exit "${FAKE_CURL_EXIT:-0}"
SH
chmod +x "$FAKE_BIN/curl"
export CURL_LOG

payload='{"message":"Claude is waiting for your input"}'

printf '%s' "$payload" \
  | env -u PUSHOVER_API_TOKEN -u PUSHOVER_USER_KEY \
      PATH="$FAKE_BIN:$PATH" bash "$HOOK"
[ ! -e "$CURL_LOG" ] || { echo "FAIL: curl ran without credentials" >&2; exit 1; }

printf '%s' "$payload" \
  | env -u PUSHOVER_USER_KEY PUSHOVER_API_TOKEN=token \
      PATH="$FAKE_BIN:$PATH" bash "$HOOK"
[ ! -e "$CURL_LOG" ] || { echo "FAIL: curl ran with only the API token" >&2; exit 1; }

printf '%s' "$payload" \
  | env -u PUSHOVER_API_TOKEN PUSHOVER_USER_KEY=user \
      PATH="$FAKE_BIN:$PATH" bash "$HOOK"
[ ! -e "$CURL_LOG" ] || { echo "FAIL: curl ran with only the user key" >&2; exit 1; }

printf '%s' "$payload" \
  | env PUSHOVER_API_TOKEN=token PUSHOVER_USER_KEY=user FAKE_CURL_EXIT=28 \
      PATH="$FAKE_BIN:$PATH" bash "$HOOK"

grep -Fxq -- '--connect-timeout' "$CURL_LOG"
grep -Fxq -- '3' "$CURL_LOG"
grep -Fxq -- '--max-time' "$CURL_LOG"
grep -Fxq -- '5' "$CURL_LOG"
grep -Fxq -- 'message=Claudeはあなたの入力を待っています' "$CURL_LOG"
grep -Fxq -- 'https://api.pushover.net/1/messages.json' "$CURL_LOG"

echo "Claude notification tests: ok"
