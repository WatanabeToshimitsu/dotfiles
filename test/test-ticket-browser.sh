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
if [ "$*" = "get url" ] && [ -f "${FAKE_AGENT_BROWSER_LOG:?}" ]; then
  printf '%s\n' "${FAKE_AGENT_BROWSER_URL-https://app.notion.com/p/abc}"
  printf 'CHECK=%s\n' "$*" >> "$FAKE_AGENT_BROWSER_LOG.checks"
  exit 0
fi
if [ "$*" = back ] && [ -f "${FAKE_AGENT_BROWSER_LOG:?}" ]; then
  printf 'BACK\n' >> "${FAKE_AGENT_BROWSER_LOG:?}.checks"
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
  rm -f "$FAKE_AGENT_BROWSER_LOG" "$FAKE_AGENT_BROWSER_LOG.checks"
  "$LAUNCHER" "$@" > /dev/null 2> "$TEST_OUTPUT_DIR/err" \
    || fail "rejected: $* ($(cat "$TEST_OUTPUT_DIR/err"))"
  [ -f "$FAKE_AGENT_BROWSER_LOG" ] || fail "agent-browser was not called: $*"
}

run_rejected() {
  rm -f "$FAKE_AGENT_BROWSER_LOG" "$FAKE_AGENT_BROWSER_LOG.checks"
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
run_rejected open https://app.notion.com/p/abc https://example.com/
run_rejected find alt logo click
run_rejected find testid x click
run_rejected
run_ok snapshot -i -c -d 3 -s main
run_ok screenshot --full shot.png
run_ok find text Done click --exact
run_ok wait --url "**/p/*"
for args in "get url -s other" "click @e1 -i" "find role button click -d 2" \
  "snapshot --name x" "wait --full" "get text --load x"; do
  # shellcheck disable=SC2086
  run_rejected $args
done

# The exit status of the browser call reaches the caller.
cat > "$TEST_OUTPUT_DIR/bin/agent-browser-failing" <<'FAILING'
#!/usr/bin/env bash
[ "${1:-}" = "--version" ] && { echo "agent-browser 0.39.1"; exit 0; }
[ "$*" = "get url" ] && { echo "https://app.notion.com/p/abc"; exit 0; }
exit 7
FAILING
chmod +x "$TEST_OUTPUT_DIR/bin/agent-browser-failing"
mkdir -p "$TEST_OUTPUT_DIR/failing-bin"
ln -s "$TEST_OUTPUT_DIR/bin/agent-browser-failing" "$TEST_OUTPUT_DIR/failing-bin/agent-browser"
for command in "get title" "click @e1"; do
  status=0
  # shellcheck disable=SC2086
  PATH="$TEST_OUTPUT_DIR/failing-bin:$PATH" "$LAUNCHER" $command > /dev/null 2>&1 || status=$?
  [ "$status" = 7 ] || fail "exit status $status instead of 7 for: $command"
done

# The launcher works when installed through a symlinked directory.
mkdir -p "$TEST_OUTPUT_DIR/linked-home"
ln -s "$REPO_DIR/.shell-utils" "$TEST_OUTPUT_DIR/linked-home/.shell-utils"
rm -f "$FAKE_AGENT_BROWSER_LOG"
"$TEST_OUTPUT_DIR/linked-home/.shell-utils/ticket-browser" get url > /dev/null \
  || fail "launcher failed through a symlinked directory"
assert_contains "AGENT_BROWSER_ACTION_POLICY=$POLICY" "$FAKE_AGENT_BROWSER_LOG"

# An action that leaves Notion is undone and reported as a failure.
for command in "open https://app.notion.com/p/abc" back reload "find role button click" \
  "click @e1" "press Enter" "select @e1 a" "check @e1" "uncheck @e1"; do
  # shellcheck disable=SC2086
  run_ok $command
  grep -Fxq 'CHECK=get url' "$FAKE_AGENT_BROWSER_LOG.checks" \
    || fail "$command was not followed by a URL check"
done
rm -f "$FAKE_AGENT_BROWSER_LOG" "$FAKE_AGENT_BROWSER_LOG.checks"
if FAKE_AGENT_BROWSER_URL='' "$LAUNCHER" click @e1 > /dev/null 2> "$TEST_OUTPUT_DIR/err"; then
  fail "an unknown page was accepted"
fi
grep -Fq "could not read the page URL" "$TEST_OUTPUT_DIR/err" || fail "unknown page gave no reason"
! grep -Fxq BACK "$FAKE_AGENT_BROWSER_LOG.checks" || fail "unknown page was navigated back"
for url in https://github.com/org/repo/pull/1 'https://notion.com.evil.example/'; do
  rm -f "$FAKE_AGENT_BROWSER_LOG.checks"
  rm -f "$FAKE_AGENT_BROWSER_LOG"
  if FAKE_AGENT_BROWSER_URL="$url" "$LAUNCHER" click @e1 > /dev/null 2> "$TEST_OUTPUT_DIR/err"; then
    fail "navigation to $url was accepted"
  fi
  grep -Fxq BACK "$FAKE_AGENT_BROWSER_LOG.checks" || fail "navigation to $url was not undone"
  grep -Fq "left Notion" "$TEST_OUTPUT_DIR/err" || fail "navigation to $url gave no reason"
done
FAKE_AGENT_BROWSER_URL=about:blank run_ok press Enter
rm -f "$FAKE_AGENT_BROWSER_LOG.checks"
FAKE_AGENT_BROWSER_URL=https://github.com/ run_ok close
[ ! -f "$FAKE_AGENT_BROWSER_LOG.checks" ] || fail "close was followed by a URL check"

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
  session="tb-test-$$"
  jq --arg s "$session" '.session = $s | .headed = false' "$CONFIG" > "$TEST_OUTPUT_DIR/real-config.json"
  printf '{}\n' > "$TEST_OUTPUT_DIR/empty-config.json"
  real() {
    env -i PATH="$REAL_PATH" HOME="$REAL_HOME" \
      AGENT_BROWSER_CONFIG="$TEST_OUTPUT_DIR/real-config.json" \
      AGENT_BROWSER_ACTION_POLICY="$POLICY" agent-browser "$@"
  }
  unrestricted() {
    env -i PATH="$REAL_PATH" HOME="$REAL_HOME" AGENT_BROWSER_SESSION="$session-open" \
      AGENT_BROWSER_CONFIG="$TEST_OUTPUT_DIR/empty-config.json" agent-browser "$@"
  }
  cleanup_real() {
    real close > /dev/null 2>&1 || true
    unrestricted close > /dev/null 2>&1 || true
  }
  trap 'cleanup_real; rm -rf "$TEST_OUTPUT_DIR"' EXIT

  unrestricted open about:blank > /dev/null
  [ "$(unrestricted eval 1+1 2>&1 | tail -n 1)" = 2 ] || fail "control: eval did not run without the policy"

  page='data:text/html,<input id=a><input id=c type=checkbox><select id=s><option>x</option></select><button id=b>Go</button>'
  real open "$page" > /dev/null || fail "installed agent-browser denied: open"
  env -i PATH="$REAL_PATH" HOME="$REAL_HOME" agent-browser session list 2>&1 | grep -Fq "$session" || fail "config session key was ignored"
  for command in "fill #a x" "type #a y" "click #b" "press Tab" "hover #b" "focus #a" \
    "check #c" "uncheck #c" "select #s x" "find role button click --name Go" \
    "get text #b" "get value #a" "get attr #a id" "get title" "get url" "get count input" \
    "is visible #a" "is enabled #a" "is checked #c" "scroll down 10" "scrollintoview #b" \
    "wait 10" "wait --load load" "snapshot -i -c" "screenshot $TEST_OUTPUT_DIR/shot.png" \
    reload "open data:text/html,<p>2</p>" back; do
    # shellcheck disable=SC2086
    real $command > "$TEST_OUTPUT_DIR/real.out" 2>&1 \
      || fail "installed agent-browser denied: $command ($(tail -n 1 "$TEST_OUTPUT_DIR/real.out"))"
  done
  for command in "eval 1" "cookies get" "storage local" "state save $TEST_OUTPUT_DIR/s.json" \
    "network requests" "get cdp-url" "tab new" "find alt x click"; do
    # shellcheck disable=SC2086
    if real $command > "$TEST_OUTPUT_DIR/real.out" 2>&1 \
      || ! grep -q "denied by policy\|not in the allow list" "$TEST_OUTPUT_DIR/real.out"; then
      fail "installed agent-browser did not deny: $command"
    fi
  done
fi

printf 'ticket-browser tests passed\n'
