#!/usr/bin/env bash
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$TEST_DIR/.." && pwd)"
LAUNCHER="$REPO_DIR/.shell-utils/claude-sandbox"
SETTINGS="$REPO_DIR/claude/sandbox-canary.json"
TEST_OUTPUT_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_OUTPUT_DIR"' EXIT

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  local expected="$1" file="$2"
  grep -Fq -- "$expected" "$file" || fail "missing output: $expected"
}

mkdir -p "$TEST_OUTPUT_DIR/bin"
cat > "$TEST_OUTPUT_DIR/bin/claude" <<'FAKE_CLAUDE'
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "--version" ]; then
  printf '%s (Claude Code)\n' "${FAKE_CLAUDE_VERSION:?}"
  exit 0
fi
printf '%s\n' "$@"
FAKE_CLAUDE
chmod +x "$TEST_OUTPUT_DIR/bin/claude"

cat > "$TEST_OUTPUT_DIR/bin/uname" <<'FAKE_UNAME'
#!/usr/bin/env bash
printf '%s\n' "${FAKE_UNAME:?}"
FAKE_UNAME
chmod +x "$TEST_OUTPUT_DIR/bin/uname"

export PATH="$TEST_OUTPUT_DIR/bin:$PATH"
export CLAUDE_SANDBOX_SETTINGS="$SETTINGS"
export FAKE_UNAME=Darwin

FAKE_CLAUDE_VERSION=2.1.231 "$LAUNCHER" --check \
  > "$TEST_OUTPUT_DIR/check-231.out" 2> "$TEST_OUTPUT_DIR/check-231.err"
assert_contains "Sandbox canary ready on macOS with Claude Code 2.1.231." "$TEST_OUTPUT_DIR/check-231.out"
[ ! -s "$TEST_OUTPUT_DIR/check-231.err" ] || fail "check emitted an unexpected warning"

if FAKE_CLAUDE_VERSION=2.1.186 "$LAUNCHER" --check \
  > "$TEST_OUTPUT_DIR/check-old.out" 2> "$TEST_OUTPUT_DIR/check-old.err"; then
  fail "Claude Code without credential protection was accepted"
fi
assert_contains "2.1.187 or later is required" "$TEST_OUTPUT_DIR/check-old.err"

if FAKE_UNAME=Linux FAKE_CLAUDE_VERSION=2.1.231 "$LAUNCHER" --check \
  > "$TEST_OUTPUT_DIR/check-linux.out" 2> "$TEST_OUTPUT_DIR/check-linux.err"; then
  fail "unsupported platform was accepted"
fi
assert_contains "only supported on macOS" "$TEST_OUTPUT_DIR/check-linux.err"

FAKE_CLAUDE_VERSION=2.1.231 "$LAUNCHER" --model opus \
  > "$TEST_OUTPUT_DIR/launch.out" 2> "$TEST_OUTPUT_DIR/launch.err"
assert_contains "--settings" "$TEST_OUTPUT_DIR/launch.out"
assert_contains "$SETTINGS" "$TEST_OUTPUT_DIR/launch.out"
assert_contains "--model" "$TEST_OUTPUT_DIR/launch.out"
assert_contains "opus" "$TEST_OUTPUT_DIR/launch.out"

printf 'claude sandbox canary tests: ok\n'
