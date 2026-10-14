#!/usr/bin/env bash
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -P "$TEST_DIR/.." && pwd)"
LAUNCHER="$REPO_DIR/.shell-utils/ticket-browser"
POLICY="$REPO_DIR/.shell-utils/ticket-browser-policy.json"
CONFIG="$REPO_DIR/.shell-utils/ticket-browser.json"
TEST_OUTPUT_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_OUTPUT_DIR"' EXIT

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  local expected="$1" file="$2"
  grep -Fxq -- "$expected" "$file" || fail "missing line: $expected"
}

mkdir -p "$TEST_OUTPUT_DIR/bin" "$TEST_OUTPUT_DIR/home"
cat > "$TEST_OUTPUT_DIR/bin/agent-browser" <<'FAKE_AGENT_BROWSER'
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "--version" ]; then
  printf 'agent-browser %s\n' "${FAKE_AGENT_BROWSER_VERSION:?}"
  exit 0
fi
{
  env | grep '^AGENT_BROWSER_' | sort
  printf 'ARG=%s\n' "$@"
} > "${FAKE_AGENT_BROWSER_LOG:?}"
FAKE_AGENT_BROWSER
chmod +x "$TEST_OUTPUT_DIR/bin/agent-browser"

REAL_PATH="$PATH"
REAL_HOME="$HOME"
export PATH="$TEST_OUTPUT_DIR/bin:$PATH"
export HOME="$TEST_OUTPUT_DIR/home"
export FAKE_AGENT_BROWSER_VERSION=0.39.1
export FAKE_AGENT_BROWSER_LOG="$TEST_OUTPUT_DIR/call.log"

run_ok() {
  rm -f "$FAKE_AGENT_BROWSER_LOG"
  "$LAUNCHER" "$@" > /dev/null 2> "$TEST_OUTPUT_DIR/err" \
    || fail "rejected: $* ($(cat "$TEST_OUTPUT_DIR/err"))"
  [ -f "$FAKE_AGENT_BROWSER_LOG" ] || fail "agent-browser was not called: $*"
}

run_rejected() {
  rm -f "$FAKE_AGENT_BROWSER_LOG"
  if "$LAUNCHER" "$@" > /dev/null 2> "$TEST_OUTPUT_DIR/err"; then
    fail "accepted: $*"
  fi
  [ ! -f "$FAKE_AGENT_BROWSER_LOG" ] || fail "agent-browser was called: $*"
  [ -s "$TEST_OUTPUT_DIR/err" ] || fail "no reason given: $*"
}

# The launcher pins its own configuration and drops caller overrides.
AGENT_BROWSER_ALLOWED_DOMAINS=evil.example AGENT_BROWSER_CDP=9222 \
  AGENT_BROWSER_SESSION=other run_ok open https://app.notion.com/p/abc
assert_contains "AGENT_BROWSER_CONFIG=$CONFIG" "$FAKE_AGENT_BROWSER_LOG"
assert_contains "AGENT_BROWSER_ACTION_POLICY=$POLICY" "$FAKE_AGENT_BROWSER_LOG"
assert_contains "AGENT_BROWSER_PROFILE=$HOME/.agent-browser/profiles/ticket" "$FAKE_AGENT_BROWSER_LOG"
[ "$(grep -c '^AGENT_BROWSER_' "$FAKE_AGENT_BROWSER_LOG")" = 3 ] \
  || fail "caller AGENT_BROWSER_* variables leaked through"
assert_contains "ARG=open" "$FAKE_AGENT_BROWSER_LOG"
assert_contains "ARG=https://app.notion.com/p/abc" "$FAKE_AGENT_BROWSER_LOG"

# Pages on Notion hosts open; everything else is refused.
run_ok open https://www.notion.so/team/abc?v=1
run_ok open https://notion.com/
for url in \
  https://example.com/ \
  http://app.notion.com/ \
  'https://notion.com@evil.example/' \
  https://app.notion.com.evil.example/ \
  https://evilnotion.com/ \
  https://app.notion.com:8443/ \
  'javascript:alert(1)' \
  file:///etc/hosts \
  'data:text/html,<b>x</b>'; do
  run_rejected open "$url"
done
run_rejected open

# Only the commands the ticket workflow needs pass.
run_ok snapshot -i -c
run_ok find role button click --name New
run_ok get text @e1
run_ok get url
run_ok wait --load networkidle
run_ok fill @e2 "X. Example title"
run_ok press Enter
run_ok close
for command in eval cookies storage state network connect auth batch read \
  install upgrade skills chat tab set mouse keyboard upload download drag \
  dashboard session profiles; do
  run_rejected "$command" anything
done
run_rejected get cdp-url
run_rejected get html body
run_rejected press Control+k
run_rejected press Meta+p
run_rejected

# Options other than the few the workflow uses are refused anywhere.
for option in --session=x "--profile x" "--allowed-domains x" \
  "--action-policy x" "--config x" "--cdp 9222" --auto-connect "--state x" \
  "--namespace x" "--executable-path x" "--extension x" "--args x" "-p x" \
  "--headed false" --new-tab "--fn x"; do
  # shellcheck disable=SC2086
  run_rejected click @e1 $option
done

# The policy denies by default and never allows script or state access.
jq -e '.default == "deny"' "$POLICY" > /dev/null || fail "policy does not deny by default"
for action in evaluate cookies_get cookies_set storage_get storage_set \
  state_save state_load route requests har_start download upload auth_login \
  batch read cdp_url; do
  jq -e --arg a "$action" '.allow | index($a) | not' "$POLICY" > /dev/null \
    || fail "policy allows $action"
done
jq -e '(.allowedDomains // .cdp // .autoConnect // .args // .extensions // .provider) == null' \
  "$CONFIG" > /dev/null || fail "config enables an unsafe connection option"

# A missing or permissive policy and an old agent-browser fail closed.
mkdir -p "$TEST_OUTPUT_DIR/copy"
cp "$LAUNCHER" "$CONFIG" "$TEST_OUTPUT_DIR/copy/"
COPY="$TEST_OUTPUT_DIR/copy/ticket-browser"
rm -f "$FAKE_AGENT_BROWSER_LOG"
if "$COPY" get url > /dev/null 2>&1; then fail "missing policy was accepted"; fi
printf '{"default":"allow"}\n' > "$TEST_OUTPUT_DIR/copy/ticket-browser-policy.json"
if "$COPY" get url > /dev/null 2>&1; then fail "permissive policy was accepted"; fi
[ ! -f "$FAKE_AGENT_BROWSER_LOG" ] || fail "agent-browser was called without a safe policy"
FAKE_AGENT_BROWSER_VERSION=0.39.0 run_rejected get url

# Opt-in: the installed agent-browser enforces the policy's action names.
if [ "${TICKET_BROWSER_REAL:-}" = 1 ]; then
  real() {
    PATH="$REAL_PATH" HOME="$REAL_HOME" AGENT_BROWSER_SESSION="tb-test-$$" \
      AGENT_BROWSER_ACTION_POLICY="$POLICY" agent-browser "$@"
  }
  real open about:blank > /dev/null
  for command in "eval 1" "cookies get" "storage local" "state save $TEST_OUTPUT_DIR/s.json" \
    "network requests" "get cdp-url"; do
    # shellcheck disable=SC2086
    if real $command > "$TEST_OUTPUT_DIR/real.out" 2>&1 \
      || ! grep -q "denied by policy\|not in the allow list" "$TEST_OUTPUT_DIR/real.out"; then
      real close > /dev/null 2>&1 || true
      fail "installed agent-browser did not deny: $command"
    fi
  done
  real get url > /dev/null || fail "installed agent-browser denied an allowed action"
  real close > /dev/null
fi

printf 'ticket-browser tests passed\n'
