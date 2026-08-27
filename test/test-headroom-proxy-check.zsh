#!/usr/bin/env zsh
set -euo pipefail

TEST_DIR="${${(%):-%N}:A:h}"
REPO_DIR="${TEST_DIR:h}"
UTIL="$REPO_DIR/.shell-utils/headroom-proxy-check.zsh"

TEST_OUTPUT_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_OUTPUT_DIR"' EXIT

fail() {
  print -u2 "FAIL: $*"
  exit 1
}

assert_contains() {
  local expected="$1" file="$2"
  grep -Fq -- "$expected" "$file" || fail "missing output: $expected"
}

source "$UTIL"

# A reachable proxy stays silent; every new shell would otherwise be noisy.
_headroom_proxy_reachable() { return 0 }
reachable="$TEST_OUTPUT_DIR/reachable"
headroom_proxy_check > "$reachable" 2>&1
[[ ! -s "$reachable" ]] || fail "reachable proxy produced output: $(<"$reachable")"

# An unreachable proxy names the port and the command that brings it back.
_headroom_proxy_reachable() { return 1 }
unreachable="$TEST_OUTPUT_DIR/unreachable"
HEADROOM_PORT=8787
headroom_proxy_check > "$unreachable" 2>&1
assert_contains "8787" "$unreachable"
assert_contains "install.sh --headroom-only" "$unreachable"

# The warning goes to stderr so it cannot leak into captured stdout.
stdout_only="$TEST_OUTPUT_DIR/stdout-only"
headroom_proxy_check 2> /dev/null > "$stdout_only"
[[ ! -s "$stdout_only" ]] || fail "warning was written to stdout"

# The real probe reports a port with no listener as unreachable.
source "$UTIL"
if _headroom_proxy_reachable 1; then
  fail "port 1 reported as reachable"
fi

print "headroom proxy check tests: ok"
