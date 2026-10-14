#!/usr/bin/env bash
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -P "$TEST_DIR/.." && pwd)"
LAUNCHER="$REPO_DIR/.shell-utils/ticket-browser"
POLICY="$REPO_DIR/.shell-utils/ticket-browser-policy.json"
CONFIG="$REPO_DIR/.shell-utils/ticket-browser.json"
TEST_OUTPUT_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_OUTPUT_DIR"' EXIT

BOARD=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
VIEW=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
TICKET=cccccccccccccccccccccccccccccccc
OTHER=dddddddddddddddddddddddddddddddd
TICKET_URL="https://app.notion.com/p/team/1-Title-$TICKET"

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
log="${FAKE_AGENT_BROWSER_LOG:?}"
if [ "${1:-}" = "--version" ]; then
  printf 'agent-browser %s\n' "${FAKE_AGENT_BROWSER_VERSION:?}"
  exit 0
fi
if [ "${1:-}" = "--json" ]; then
  printf '%s\n' "${*:2}" >> "$log.internal"
  case "${*:2}" in
    "get url")
      url="${FAKE_AGENT_BROWSER_URL-}"
      [ -f "$log" ] || url="${FAKE_AGENT_BROWSER_URL_BEFORE-$url}"
      [ -f "$log.back" ] && url="${FAKE_AGENT_BROWSER_URL_AFTER_BACK-$url}"
      jq -cn --arg u "$url" '{success: true, data: {url: $u}}'
      ;;
    "tab list") jq -cn --argjson t "${FAKE_AGENT_BROWSER_TABS:-[]}" '{success: true, data: {tabs: $t}}' ;;
    back) touch "$log.back"; printf '{"success":true}\n' ;;
    *) printf '{"success":true}\n' ;;
  esac
  exit 0
fi
{
  env | grep '^AGENT_BROWSER_' | sort
  printf 'ARG=%s\n' "$@"
} > "$log"
exit "${FAKE_AGENT_BROWSER_STATUS:-0}"
FAKE_AGENT_BROWSER
chmod +x "$TEST_OUTPUT_DIR/bin/agent-browser"

REAL_PATH="$PATH"
REAL_HOME="$HOME"
export PATH="$TEST_OUTPUT_DIR/bin:$PATH"
export HOME="$TEST_OUTPUT_DIR/home"
export FAKE_AGENT_BROWSER_VERSION=0.39.1
export FAKE_AGENT_BROWSER_LOG="$TEST_OUTPUT_DIR/call.log"
export FAKE_AGENT_BROWSER_URL="$TICKET_URL"
PAGES="$HOME/.claude/ticket/browser-pages"

reset_log() {
  rm -f "$FAKE_AGENT_BROWSER_LOG" "$FAKE_AGENT_BROWSER_LOG.internal" "$FAKE_AGENT_BROWSER_LOG.back"
}

run_ok() {
  reset_log
  "$LAUNCHER" "$@" > /dev/null 2> "$TEST_OUTPUT_DIR/err" \
    || fail "rejected: $* ($(cat "$TEST_OUTPUT_DIR/err"))"
  [ -f "$FAKE_AGENT_BROWSER_LOG" ] || fail "agent-browser was not called: $*"
}

run_rejected() {
  reset_log
  if "$LAUNCHER" "$@" > /dev/null 2> "$TEST_OUTPUT_DIR/err"; then
    fail "accepted: $*"
  fi
  [ ! -f "$FAKE_AGENT_BROWSER_LOG" ] || fail "agent-browser was called: $*"
  [ -s "$TEST_OUTPUT_DIR/err" ] || fail "no reason given: $*"
}

# Pages are registered explicitly; registration never calls the browser.
run_rejected open "$TICKET_URL"
for url in https://example.com/p/$TICKET https://app.notion.com/login "https://app.notion.com/p/team/no-id"; do
  reset_log
  if "$LAUNCHER" allow "$url" > /dev/null 2>&1; then fail "registered: $url"; fi
done
reset_log
"$LAUNCHER" allow "https://app.notion.com/p/team/$BOARD?v=$VIEW" > /dev/null || fail "board was not registered"
"$LAUNCHER" allow "$TICKET_URL" > /dev/null || fail "ticket was not registered"
[ ! -f "$FAKE_AGENT_BROWSER_LOG.internal" ] && [ ! -f "$FAKE_AGENT_BROWSER_LOG" ] \
  || fail "registration called agent-browser"
for id in "$BOARD" "$VIEW" "$TICKET"; do assert_contains "$id" "$PAGES"; done

# The launcher pins its own configuration and drops caller overrides.
AGENT_BROWSER_ALLOWED_DOMAINS=evil.example AGENT_BROWSER_CDP=9222 \
  AGENT_BROWSER_SESSION=other run_ok open "$TICKET_URL"
assert_contains "AGENT_BROWSER_CONFIG=$CONFIG" "$FAKE_AGENT_BROWSER_LOG"
assert_contains "AGENT_BROWSER_ACTION_POLICY=$POLICY" "$FAKE_AGENT_BROWSER_LOG"
assert_contains "AGENT_BROWSER_PROFILE=$HOME/.agent-browser/profiles/ticket" "$FAKE_AGENT_BROWSER_LOG"
[ "$(grep -c '^AGENT_BROWSER_' "$FAKE_AGENT_BROWSER_LOG")" = 3 ] \
  || fail "caller AGENT_BROWSER_* variables leaked through"
assert_contains "ARG=open" "$FAKE_AGENT_BROWSER_LOG"
assert_contains "ARG=$TICKET_URL" "$FAKE_AGENT_BROWSER_LOG"

# Only registered Notion pages and the login page open.
run_ok open "https://app.notion.com/p/team/$BOARD?v=$VIEW"
run_ok open "https://www.notion.so/$TICKET"
run_ok open https://app.notion.com/login
for url in \
  "https://app.notion.com/p/team/$OTHER" \
  "https://app.notion.com/p/team/$BOARD?v=$VIEW&p=$OTHER" \
  https://app.notion.com/ \
  https://example.com/ \
  "http://app.notion.com/p/$TICKET" \
  "https://notion.com@evil.example/p/$TICKET" \
  "https://app.notion.com.evil.example/p/$TICKET" \
  "https://evilnotion.com/p/$TICKET" \
  "https://app.notion.com:8443/p/$TICKET" \
  'javascript:alert(1)' \
  file:///etc/hosts \
  'data:text/html,<b>x</b>'; do
  run_rejected open "$url"
done
run_rejected open
run_rejected open "$TICKET_URL" https://example.com/

# Only the commands and options the ticket workflow needs pass.
run_ok snapshot -i -c -d 3 -s main
run_ok screenshot --full shot.png
run_ok find role button click --name New
run_ok find text Done click --exact
run_ok find nth 2 .item text
run_ok get text @e1
run_ok get url
run_ok wait --load networkidle
run_ok wait --url "**/p/*"
run_ok fill @e2 "X. Example title"
run_ok type @e2 "- bullet text"
run_ok type @e2 "-"
run_ok press Enter
for key in Delete Home End ArrowLeft ArrowRight; do run_ok press "$key"; done
run_ok close
for command in eval cookies storage state network connect auth batch read \
  install upgrade skills chat tab set mouse keyboard upload download drag \
  dashboard session profiles clipboard; do
  run_rejected "$command" anything
done
run_rejected get cdp-url
run_rejected get html body
for key in Control+k Meta+p Shift+End; do run_rejected press "$key"; done
run_rejected find alt logo click
run_rejected find testid x click
run_rejected find role button eval
run_rejected find nth 2 .item download
run_rejected
for args in "get url -s other" "click @e1 -i" "find role button click -d 2" \
  "snapshot --name x" "wait --full" "get text --load x"; do
  # shellcheck disable=SC2086
  run_rejected $args
done
for option in --session=x "--profile x" "--allowed-domains x" \
  "--action-policy x" "--config x" "--cdp 9222" --auto-connect "--state x" \
  "--namespace x" "--executable-path x" "--extension x" "--args x" "-p x" \
  "--headed false" --new-tab "--fn x" --name=x; do
  # shellcheck disable=SC2086
  run_rejected click @e1 $option
done

# Commands other than open and close run only on a registered Notion page.
for url in "https://app.notion.com/p/team/$OTHER" "https://app.notion.com/p/team/$BOARD?v=$VIEW&p=$OTHER" \
  https://example.com/ ''; do
  reset_log
  if FAKE_AGENT_BROWSER_URL="$url" "$LAUNCHER" get text @e1 > /dev/null 2> "$TEST_OUTPUT_DIR/err"; then
    fail "read on unregistered page was accepted: $url"
  fi
  [ ! -f "$FAKE_AGENT_BROWSER_LOG" ] || fail "read ran on unregistered page: $url"
done
FAKE_AGENT_BROWSER_URL=about:blank run_ok snapshot -i
FAKE_AGENT_BROWSER_URL="https://app.notion.com/p/team/$OTHER" run_ok get url

# Navigation that leaves Notion is undone; new tabs are closed.
for command in "open $TICKET_URL" back reload "find role button click" \
  "click @e1" "press Enter" "select @e1 a" "check @e1" "uncheck @e1"; do
  # shellcheck disable=SC2086
  run_ok $command
  assert_contains "get url" "$FAKE_AGENT_BROWSER_LOG.internal"
  assert_contains "tab list" "$FAKE_AGENT_BROWSER_LOG.internal"
done
reset_log
if FAKE_AGENT_BROWSER_URL_BEFORE="$TICKET_URL" FAKE_AGENT_BROWSER_URL=https://github.com/org/repo/pull/1 FAKE_AGENT_BROWSER_URL_AFTER_BACK="$TICKET_URL" \
  "$LAUNCHER" click @e1 > /dev/null 2> "$TEST_OUTPUT_DIR/err"; then
  fail "navigation away from Notion was accepted"
fi
grep -Fq "went back" "$TEST_OUTPUT_DIR/err" || fail "navigation away gave no reason"
assert_contains back "$FAKE_AGENT_BROWSER_LOG.internal"
reset_log
if FAKE_AGENT_BROWSER_URL_BEFORE="$TICKET_URL" FAKE_AGENT_BROWSER_URL=https://github.com/ FAKE_AGENT_BROWSER_URL_AFTER_BACK=https://github.com/ \
  "$LAUNCHER" click @e1 > /dev/null 2> "$TEST_OUTPUT_DIR/err"; then
  fail "a failed return was accepted"
fi
grep -Fq "closed the browser" "$TEST_OUTPUT_DIR/err" || fail "failed return did not close the browser"
assert_contains close "$FAKE_AGENT_BROWSER_LOG.internal"
reset_log
tabs='[{"tabId":"t1","active":false,"url":"'"$TICKET_URL"'"},{"tabId":"t2","active":true,"url":"https://github.com/"}]'
if FAKE_AGENT_BROWSER_TABS="$tabs" "$LAUNCHER" click @e1 > /dev/null 2> "$TEST_OUTPUT_DIR/err"; then
  fail "a new tab outside Notion was accepted"
fi
assert_contains "tab close t2" "$FAKE_AGENT_BROWSER_LOG.internal"
grep -Fq "new tab" "$TEST_OUTPUT_DIR/err" || fail "new tab gave no reason"
reset_log
if FAKE_AGENT_BROWSER_URL_BEFORE="$TICKET_URL" FAKE_AGENT_BROWSER_URL='' "$LAUNCHER" click @e1 > /dev/null 2> "$TEST_OUTPUT_DIR/err"; then
  fail "an unknown page was accepted"
fi
grep -Fq "could not read the page URL" "$TEST_OUTPUT_DIR/err" || fail "unknown page gave no reason"
FAKE_AGENT_BROWSER_URL=about:blank run_ok press Enter
reset_log
"$LAUNCHER" close > /dev/null
[ ! -f "$FAKE_AGENT_BROWSER_LOG.internal" ] || fail "close was followed by checks"

# The exit status of the browser call reaches the caller.
for command in "get title" "click @e1"; do
  status=0
  # shellcheck disable=SC2086
  FAKE_AGENT_BROWSER_STATUS=7 "$LAUNCHER" $command > /dev/null 2>&1 || status=$?
  [ "$status" = 7 ] || fail "exit status $status instead of 7 for: $command"
done

# The launcher works when installed through a symlinked directory.
mkdir -p "$TEST_OUTPUT_DIR/linked-home"
ln -s "$REPO_DIR/.shell-utils" "$TEST_OUTPUT_DIR/linked-home/.shell-utils"
reset_log
"$TEST_OUTPUT_DIR/linked-home/.shell-utils/ticket-browser" get url > /dev/null \
  || fail "launcher failed through a symlinked directory"
assert_contains "AGENT_BROWSER_ACTION_POLICY=$POLICY" "$FAKE_AGENT_BROWSER_LOG"

# The policy denies by default and never allows script or state access.
jq -e '.default == "deny"' "$POLICY" > /dev/null || fail "policy does not deny by default"
for action in evaluate cookies_get cookies_set storage_get storage_set \
  state_save state_load route requests har_start download upload auth_login \
  batch read cdp_url tab_new clipboard; do
  jq -e --arg a "$action" '.allow | index($a) | not' "$POLICY" > /dev/null \
    || fail "policy allows $action"
done
jq -e '(.allowedDomains // .cdp // .autoConnect // .args // .extensions // .provider) == null' \
  "$CONFIG" > /dev/null || fail "config enables an unsafe connection option"

# A missing or permissive policy and an old agent-browser fail closed.
mkdir -p "$TEST_OUTPUT_DIR/copy"
cp "$LAUNCHER" "$CONFIG" "$TEST_OUTPUT_DIR/copy/"
COPY="$TEST_OUTPUT_DIR/copy/ticket-browser"
reset_log
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

  # data: pages are refused by the launcher; they only exercise the policy here.
  page='data:text/html,<input id=a><input id=c type=checkbox><select id=s><option>x</option></select><button id=b>Go</button><a id=n href="data:text/html,x" target="_blank">n</a>'
  real open "$page" > /dev/null || fail "installed agent-browser denied: open"
  env -i PATH="$REAL_PATH" HOME="$REAL_HOME" agent-browser session list 2>&1 | grep -Fq "$session" || fail "config session key was ignored"
  for command in "fill #a x" "type #a y" "click #b" "press Tab" "hover #b" "focus #a" \
    "check #c" "uncheck #c" "select #s x" "find role button click --name Go" \
    "find text Go text" "get text #b" "get value #a" "get attr #a id" "get title" "get url" \
    "get count input" "is visible #a" "is enabled #a" "is checked #c" "scroll down 10" \
    "scrollintoview #b" "wait 10" "wait --load load" "snapshot -i -c -d 3 -s body" \
    "screenshot $TEST_OUTPUT_DIR/shot.png" "--json get url" "click #n" "--json tab list" \
    "--json tab close t2" reload "open data:text/html,<p>2</p>" back; do
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
