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
NEW=eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
BOARD_URL="https://app.notion.com/p/team/$BOARD?v=$VIEW"
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
    "tab list")
      one_tab='[{"tabId":"t1","active":true,"url":"x"}]'
      if [ -f "$log" ]; then
        [ -z "${FAKE_AGENT_BROWSER_TAB_LIST_FAILS:-}" ] || exit 1
        tabs="${FAKE_AGENT_BROWSER_TABS:-$one_tab}"
      else
        [ -z "${FAKE_AGENT_BROWSER_TAB_LIST_FAILS_BEFORE:-}" ] || exit 1
        tabs="${FAKE_AGENT_BROWSER_TABS_BEFORE:-$one_tab}"
      fi
      [ -f "$log.tab-closed" ] && tabs="${FAKE_AGENT_BROWSER_TABS_AFTER_CLOSE:-$one_tab}"
      jq -cn --argjson t "$tabs" '{success: true, data: {tabs: $t}}'
      ;;
    "tab close"*) touch "$log.tab-closed"; printf '{"success":true}\n' ;;
    back | forward) touch "$log.back"; printf '{"success":true}\n' ;;
    close) [ -z "${FAKE_AGENT_BROWSER_CLOSE_FAILS:-}" ] || exit 1; printf '{"success":true}\n' ;;
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
  rm -f "$FAKE_AGENT_BROWSER_LOG" "$FAKE_AGENT_BROWSER_LOG".*
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

# expect a rejected action that ran, with the given reason
run_failed_after() {
  local reason="$1"
  shift
  reset_log
  if "$LAUNCHER" "$@" > /dev/null 2> "$TEST_OUTPUT_DIR/err"; then
    fail "accepted: $*"
  fi
  grep -Fq "$reason" "$TEST_OUTPUT_DIR/err" || fail "expected '$reason' for $*, got: $(cat "$TEST_OUTPUT_DIR/err")"
}

# Pages are registered explicitly; registration never calls the browser.
run_rejected open "$TICKET_URL"
for url in "https://example.com/p/$TICKET" https://app.notion.com/login \
  "https://app.notion.com/p/team/no-id" "$BOARD_URL&p=$OTHER" "https://app.notion.com/?x=$TICKET"; do
  reset_log
  if "$LAUNCHER" allow "$url" > /dev/null 2>&1; then fail "registered: $url"; fi
done
reset_log
"$LAUNCHER" allow "$BOARD_URL" > /dev/null || fail "board was not registered"
"$LAUNCHER" allow "$TICKET_URL" > /dev/null || fail "ticket was not registered"
[ ! -f "$FAKE_AGENT_BROWSER_LOG.internal" ] && [ ! -f "$FAKE_AGENT_BROWSER_LOG" ] \
  || fail "registration called agent-browser"
assert_contains "$BOARD $VIEW" "$PAGES"
assert_contains "$TICKET" "$PAGES"
"$LAUNCHER" allow "https://app.notion.com/p/team/2-Copied-$NEW?pvs=4&source=copy_link" > /dev/null \
  || fail "a copied link was not registered"
assert_contains "$NEW" "$PAGES"
grep -v -Fx "$NEW" "$PAGES" > "$PAGES.tmp" && mv "$PAGES.tmp" "$PAGES"

# The launcher pins its own configuration and drops caller overrides.
AGENT_BROWSER_ALLOWED_DOMAINS=evil.example AGENT_BROWSER_CDP=9222 \
  AGENT_BROWSER_SESSION=other run_ok open "$TICKET_URL"
assert_contains "AGENT_BROWSER_CONFIG=$CONFIG" "$FAKE_AGENT_BROWSER_LOG"
assert_contains "AGENT_BROWSER_ACTION_POLICY=$POLICY" "$FAKE_AGENT_BROWSER_LOG"
assert_contains "AGENT_BROWSER_PROFILE=$HOME/.agent-browser/profiles/ticket" "$FAKE_AGENT_BROWSER_LOG"
assert_contains "AGENT_BROWSER_DOWNLOAD_PATH=$HOME/.agent-browser/profiles/ticket-downloads" "$FAKE_AGENT_BROWSER_LOG"
[ -d "$HOME/.agent-browser/profiles/ticket-downloads" ] && [ ! -w "$HOME/.agent-browser/profiles/ticket-downloads" ] \
  || fail "the download directory is missing or writable"
[ "$(grep -c '^AGENT_BROWSER_' "$FAKE_AGENT_BROWSER_LOG")" = 4 ] \
  || fail "caller AGENT_BROWSER_* variables leaked through"
assert_contains "ARG=open" "$FAKE_AGENT_BROWSER_LOG"
assert_contains "ARG=$TICKET_URL" "$FAKE_AGENT_BROWSER_LOG"

# Only registered pages, with their registered view, and the login page open.
run_ok open "$BOARD_URL"
run_ok open "$BOARD_URL&pvs=18"
run_ok open "$BOARD_URL&p=$TICKET&pm=s"
run_ok open "https://www.notion.so/$TICKET"
run_ok open "https://app.notion.com/p/$TICKET?pvs=25"
run_ok open https://app.notion.com/login
run_ok open "https://www.notion.so/login?redirectURL=%2Fp%2Fx"
run_ok open "$TICKET_URL#$OTHER"
FAKE_AGENT_BROWSER_URL="https://app.notion.com/p/team/1-%E3%83%86%E3%82%B9-$TICKET" run_ok open "https://app.notion.com/p/$TICKET"
FAKE_AGENT_BROWSER_URL="https://app.notion.com/p/team/1062-Web-Auto-$TICKET" run_ok open "https://app.notion.com/p/$TICKET"
for url in \
  "https://app.notion.com/p/team/$OTHER" \
  "https://app.notion.com/p/team/$BOARD" \
  "https://app.notion.com/p/team/$BOARD?v=$OTHER" \
  "$BOARD_URL&p=$OTHER" \
  "$BOARD_URL&v=$VIEW" \
  "https://app.notion.com/p/team/$VIEW" \
  "https://app.notion.com/?x=$TICKET" \
  "https://app.notion.com/p/team/$OTHER?p=$TICKET" \
  "$TICKET_URL?foo=1" \
  "$TICKET_URL#notahexanchor" \
  "https://app.notion.com/login/../p/team/$OTHER" \
  "https://www.notion.so/login#x" \
  "https://app.notion.com/p/team/%63${TICKET:1}" \
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
run_rejected find role textbox type x
run_rejected expect-new extra
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

# Commands other than open, close, and get url run only on a registered page.
for url in "https://app.notion.com/p/team/$OTHER" "$BOARD_URL&p=$OTHER" \
  "https://app.notion.com/p/team/$BOARD" https://example.com/ ''; do
  reset_log
  if FAKE_AGENT_BROWSER_URL="$url" "$LAUNCHER" get text @e1 > /dev/null 2> "$TEST_OUTPUT_DIR/err"; then
    fail "read on unregistered page was accepted: $url"
  fi
  [ ! -f "$FAKE_AGENT_BROWSER_LOG" ] || fail "read ran on unregistered page: $url"
done
FAKE_AGENT_BROWSER_URL=about:blank run_ok snapshot -i
FAKE_AGENT_BROWSER_URL_BEFORE="https://app.notion.com/p/team/$OTHER" FAKE_AGENT_BROWSER_URL_AFTER_BACK="$TICKET_URL" \
  run_failed_after "went back" get text @e1
[ ! -f "$FAKE_AGENT_BROWSER_LOG" ] || fail "the command ran on an unregistered page"
assert_contains back "$FAKE_AGENT_BROWSER_LOG.internal"
FAKE_AGENT_BROWSER_URL_BEFORE="$TICKET_URL" FAKE_AGENT_BROWSER_URL="https://app.notion.com/p/team/$OTHER" \
  FAKE_AGENT_BROWSER_URL_AFTER_BACK="$TICKET_URL" run_failed_after "went forward" back
assert_contains forward "$FAKE_AGENT_BROWSER_LOG.internal"
FAKE_AGENT_BROWSER_URL="https://app.notion.com/p/team/$OTHER" run_ok get url

# Every command that runs, other than close and get url, is checked afterwards.
for command in "open $TICKET_URL" back reload "find role button click" "click @e1" \
  "press Enter" "select @e1 a" "check @e1" "uncheck @e1" "type @e1 x" "fill @e1 x" \
  "focus @e1" "hover @e1" "scroll down 10" "wait 10" "snapshot -i" "get text @e1"; do
  # shellcheck disable=SC2086
  run_ok $command
  assert_contains "get url" "$FAKE_AGENT_BROWSER_LOG.internal"
  assert_contains "tab list" "$FAKE_AGENT_BROWSER_LOG.internal"
done
reset_log
"$LAUNCHER" close > /dev/null
[ ! -f "$FAKE_AGENT_BROWSER_LOG.internal" ] || fail "close was followed by checks"

# Reaching an unregistered page is undone; a failed return closes the browser.
FAKE_AGENT_BROWSER_URL_BEFORE="$TICKET_URL" FAKE_AGENT_BROWSER_URL=https://github.com/org/repo/pull/1 \
  FAKE_AGENT_BROWSER_URL_AFTER_BACK="$TICKET_URL" run_failed_after "went back" click @e1
assert_contains back "$FAKE_AGENT_BROWSER_LOG.internal"
FAKE_AGENT_BROWSER_URL_BEFORE="$TICKET_URL" FAKE_AGENT_BROWSER_URL="https://app.notion.com/p/team/$OTHER" \
  FAKE_AGENT_BROWSER_URL_AFTER_BACK="$TICKET_URL" run_failed_after "went back" click @e1
FAKE_AGENT_BROWSER_URL_BEFORE="$TICKET_URL" FAKE_AGENT_BROWSER_URL="https://app.notion.com/p/team/$OTHER" \
  FAKE_AGENT_BROWSER_URL_AFTER_BACK="https://app.notion.com/p/team/$OTHER" \
  run_failed_after "closed the browser" click @e1
assert_contains close "$FAKE_AGENT_BROWSER_LOG.internal"
FAKE_AGENT_BROWSER_URL_BEFORE="$TICKET_URL" FAKE_AGENT_BROWSER_URL='' \
  run_failed_after "could not read the page URL" click @e1
assert_contains close "$FAKE_AGENT_BROWSER_LOG.internal"
FAKE_AGENT_BROWSER_URL=about:blank run_ok press Enter

# A new tab is closed and confirmed gone; unverifiable tabs close the browser.
two_tabs='[{"tabId":"t2","active":true,"url":"https://github.com/"},{"tabId":"t1","active":false,"url":"a"}]'
FAKE_AGENT_BROWSER_TABS="$two_tabs" run_failed_after "new tab" click @e1
assert_contains "tab close t2" "$FAKE_AGENT_BROWSER_LOG.internal"
grep -Fxq "tab close t1" "$FAKE_AGENT_BROWSER_LOG.internal" && fail "the working tab was closed"
FAKE_AGENT_BROWSER_TABS_BEFORE='[{"tabId":"t1","active":false,"url":"a"},{"tabId":"t3","active":true,"url":"b"}]' \
  FAKE_AGENT_BROWSER_TABS_AFTER_CLOSE='[{"tabId":"t3","active":true,"url":"b"}]' run_ok get title
assert_contains "tab close t1" "$FAKE_AGENT_BROWSER_LOG.internal"
grep -Fxq "tab close t3" "$FAKE_AGENT_BROWSER_LOG.internal" && fail "the active tab was closed before the action"
FAKE_AGENT_BROWSER_TABS="$two_tabs" FAKE_AGENT_BROWSER_TABS_AFTER_CLOSE="$two_tabs" \
  run_failed_after "closed the browser" click @e1
assert_contains close "$FAKE_AGENT_BROWSER_LOG.internal"
FAKE_AGENT_BROWSER_TAB_LIST_FAILS=1 run_failed_after "closed the browser" click @e1
assert_contains close "$FAKE_AGENT_BROWSER_LOG.internal"
FAKE_AGENT_BROWSER_TABS="$two_tabs" FAKE_AGENT_BROWSER_URL_BEFORE="$TICKET_URL" \
  FAKE_AGENT_BROWSER_URL="https://app.notion.com/p/team/$OTHER" FAKE_AGENT_BROWSER_URL_AFTER_BACK="$TICKET_URL" \
  run_failed_after "went back" click @e1
grep -Fq "new tab" "$TEST_OUTPUT_DIR/err" || fail "a closed new tab was not reported with the return"
FAKE_AGENT_BROWSER_TAB_LIST_FAILS_BEFORE=1 run_failed_after "closed the browser" click @e1
[ ! -f "$FAKE_AGENT_BROWSER_LOG" ] || fail "the action ran without a readable tab list"
FAKE_AGENT_BROWSER_TABS_BEFORE="$two_tabs" FAKE_AGENT_BROWSER_TABS_AFTER_CLOSE="$two_tabs" \
  run_failed_after "closed the browser" click @e1
[ ! -f "$FAKE_AGENT_BROWSER_LOG" ] || fail "the action ran with leftover tabs"
FAKE_AGENT_BROWSER_TAB_LIST_FAILS=1 FAKE_AGENT_BROWSER_CLOSE_FAILS=1 \
  run_failed_after "closing the browser failed" click @e1

# expect-new admits exactly one new page peeked from the registered board.
FAKE_AGENT_BROWSER_URL_BEFORE="$BOARD_URL" FAKE_AGENT_BROWSER_URL="$BOARD_URL&p=$OTHER&pm=s" \
  FAKE_AGENT_BROWSER_URL_AFTER_BACK="$BOARD_URL" run_failed_after "went back" click @e1
grep -Fxq "$OTHER" "$PAGES" && fail "a peek without expect-new was registered"
reset_log
"$LAUNCHER" expect-new > /dev/null || fail "expect-new was refused"
[ ! -f "$FAKE_AGENT_BROWSER_LOG.internal" ] || fail "expect-new called agent-browser"
FAKE_AGENT_BROWSER_URL_BEFORE="$BOARD_URL" FAKE_AGENT_BROWSER_URL="$BOARD_URL&p=$NEW&pm=s" run_ok click @e1
assert_contains "$NEW" "$PAGES"
FAKE_AGENT_BROWSER_URL_BEFORE="$BOARD_URL" FAKE_AGENT_BROWSER_URL="$BOARD_URL&p=$OTHER&pm=s" \
  FAKE_AGENT_BROWSER_URL_AFTER_BACK="$BOARD_URL" run_failed_after "went back" click @e1
"$LAUNCHER" expect-new > /dev/null
FAKE_AGENT_BROWSER_URL_BEFORE="$TICKET_URL" FAKE_AGENT_BROWSER_URL="https://app.notion.com/p/team/$OTHER" \
  FAKE_AGENT_BROWSER_URL_AFTER_BACK="$TICKET_URL" run_failed_after "went back" click @e1
grep -Fxq "$OTHER" "$PAGES" && fail "expect-new registered a page outside the board"
"$LAUNCHER" expect-new > /dev/null
FAKE_AGENT_BROWSER_URL_BEFORE="$TICKET_URL" FAKE_AGENT_BROWSER_URL="$BOARD_URL&p=$OTHER&pm=s" \
  FAKE_AGENT_BROWSER_URL_AFTER_BACK="$TICKET_URL" run_failed_after "went back" click @e1
grep -Fxq "$OTHER" "$PAGES" && fail "expect-new registered a page not reached from the board"
for between in "get url" close "eval 1" "open https://example.com/"; do
  "$LAUNCHER" expect-new > /dev/null
  # shellcheck disable=SC2086
  "$LAUNCHER" $between > /dev/null 2>&1 || true
  FAKE_AGENT_BROWSER_URL_BEFORE="$BOARD_URL" FAKE_AGENT_BROWSER_URL="$BOARD_URL&p=$OTHER&pm=s" \
    FAKE_AGENT_BROWSER_URL_AFTER_BACK="$BOARD_URL" run_failed_after "went back" click @e1
  grep -Fxq "$OTHER" "$PAGES" && fail "expect-new outlived: $between"
done

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
  page='data:text/html,<label for=a>Name</label><input id=a placeholder=ph title=tt><input id=c type=checkbox><select id=s><option>x</option></select><button id=b>Go</button><a id=n href="data:text/html,x" target="_blank">n</a>'
  real open "$page" > /dev/null || fail "installed agent-browser denied: open"
  env -i PATH="$REAL_PATH" HOME="$REAL_HOME" agent-browser session list 2>&1 | grep -Fq "$session" || fail "config session key was ignored"
  for command in "fill #a x" "type #a y" "click #b" "press Tab" "hover #b" "focus #a" \
    "check #c" "uncheck #c" "select #s x" "find role button click --name Go" \
    "find text Go text" "find label Name fill z" "find placeholder ph fill w" \
    "find title tt hover" "find nth 0 input click" "find role checkbox check" \
    "get text #b" "get value #a" "get attr #a id" "get title" "get url" \
    "get count input" "is visible #a" "is enabled #a" "is checked #c" "scroll down 10" \
    "scrollintoview #b" "wait 10" "wait --load load" "wait --text Go" "wait --url data:**" \
    "snapshot -i -c -d 3 -s body" "screenshot $TEST_OUTPUT_DIR/shot.png" "--json get url" \
    "click #n" "--json tab list" "--json tab close t2" reload "open data:text/html,<p>2</p>" back; do
    # shellcheck disable=SC2086
    real $command > "$TEST_OUTPUT_DIR/real.out" 2>&1 \
      || fail "installed agent-browser denied: $command ($(tail -n 1 "$TEST_OUTPUT_DIR/real.out"))"
  done
  # A click on a download link saves nothing when the download directory is read-only.
  blocked="$TEST_OUTPUT_DIR/blocked-downloads"
  mkdir -p "$blocked" && chmod 500 "$blocked"
  probe="tb-download-probe-$$.txt"
  touch "$TEST_OUTPUT_DIR/download-marker"
  download_into() {
    local directory="$1"
    downloading() {
      env -i PATH="$REAL_PATH" HOME="$REAL_HOME" AGENT_BROWSER_CONFIG="$TEST_OUTPUT_DIR/real-config.json" \
        AGENT_BROWSER_ACTION_POLICY="$POLICY" AGENT_BROWSER_DOWNLOAD_PATH="$directory" \
        AGENT_BROWSER_SESSION="$session-dl" agent-browser "$@"
    }
    downloading open "data:text/html,<a id=d href='data:text/plain,x' download=$probe>d</a>" > /dev/null
    downloading click '#d' > /dev/null || fail "the download link could not be clicked"
    downloading wait 2000 > /dev/null
    downloading close > /dev/null
  }
  mkdir -p "$TEST_OUTPUT_DIR/writable-downloads"
  download_into "$TEST_OUTPUT_DIR/writable-downloads"
  [ -n "$(find "$TEST_OUTPUT_DIR/writable-downloads" -name "$probe*")" ] \
    || fail "control: the download link saved nothing into a writable directory"
  download_into "$blocked"
  [ -z "$(find "$blocked" "$REAL_HOME/Downloads" -name "$probe*" -newer "$TEST_OUTPUT_DIR/download-marker" 2> /dev/null)" ] \
    || fail "a click-triggered download was saved"
  chmod 700 "$blocked"

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
