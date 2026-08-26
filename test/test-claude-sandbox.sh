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

export PATH="$TEST_OUTPUT_DIR/bin:$PATH"
export CLAUDE_SANDBOX_SETTINGS="$SETTINGS"

FAKE_CLAUDE_VERSION=2.1.231 "$LAUNCHER" --check \
  > "$TEST_OUTPUT_DIR/check-231.out" 2> "$TEST_OUTPUT_DIR/check-231.err"
assert_contains "Sandbox canary ready with Claude Code 2.1.231." "$TEST_OUTPUT_DIR/check-231.out"
assert_contains "2.1.243 or later improves network-violation diagnostics" "$TEST_OUTPUT_DIR/check-231.err"

FAKE_CLAUDE_VERSION=2.1.243 "$LAUNCHER" --check \
  > "$TEST_OUTPUT_DIR/check-243.out" 2> "$TEST_OUTPUT_DIR/check-243.err"
assert_contains "Sandbox canary ready with Claude Code 2.1.243." "$TEST_OUTPUT_DIR/check-243.out"
[ ! -s "$TEST_OUTPUT_DIR/check-243.err" ] || fail "2.1.243 emitted an unexpected warning"

if FAKE_CLAUDE_VERSION=2.1.223 "$LAUNCHER" --check \
  > "$TEST_OUTPUT_DIR/check-old.out" 2> "$TEST_OUTPUT_DIR/check-old.err"; then
  fail "unsupported Claude Code version was accepted"
fi
assert_contains "2.1.224 or later is required" "$TEST_OUTPUT_DIR/check-old.err"

FAKE_CLAUDE_VERSION=2.1.243 "$LAUNCHER" --model opus \
  > "$TEST_OUTPUT_DIR/launch.out" 2> "$TEST_OUTPUT_DIR/launch.err"
assert_contains "--settings" "$TEST_OUTPUT_DIR/launch.out"
assert_contains "$SETTINGS" "$TEST_OUTPUT_DIR/launch.out"
assert_contains "--model" "$TEST_OUTPUT_DIR/launch.out"
assert_contains "opus" "$TEST_OUTPUT_DIR/launch.out"

printf 'claude sandbox canary tests: ok\n'
