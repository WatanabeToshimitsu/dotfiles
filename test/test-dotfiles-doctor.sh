#!/usr/bin/env bash
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$TEST_DIR/.." && pwd)"
# shellcheck source=../.shell-utils/dotfiles-doctor.sh
source "$REPO_DIR/.shell-utils/dotfiles-doctor.sh"

TEST_OUTPUT_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_OUTPUT_DIR"' EXIT

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  local expected="$1" file="$2"
  grep -Fq "$expected" "$file" || fail "missing output: $expected"
}

assert_not_contains() {
  local unexpected="$1" file="$2"
  if grep -Fq "$unexpected" "$file"; then
    fail "unexpected output: $unexpected"
  fi
}

set +e
run_with_timeout 0.1 bash -c 'sleep 2'
timeout_status=$?
set -e
[ "$timeout_status" -eq 124 ] || fail "run_with_timeout returned $timeout_status, expected 124"

has_command() {
  return 0
}

headroom_deployment_configured() {
  return 0
}

run_headroom_status() {
  printf 'Status: running\nHealthy: yes\n'
}

run_brew_leaves() {
  printf '%s\n' \
    'daipeihust/tap/im-select' \
    'jandedobbeleer/oh-my-posh/oh-my-posh' \
    'example/tap/untracked-formula'
}

brew_output="$TEST_OUTPUT_DIR/brew"
WARNINGS=0
check_brew_drift > "$brew_output"
[ "$WARNINGS" -eq 1 ] || fail "brew fixture produced $WARNINGS warning(s), expected 1"
assert_contains "installed but untracked: untracked-formula" "$brew_output"
assert_not_contains "installed but untracked: im-select" "$brew_output"
assert_not_contains "installed but untracked: oh-my-posh" "$brew_output"

run_headroom_savings() {
  printf 'No shaped requests recorded yet.\n'
}

run_claude_mcp_list() {
  printf 'context7: command - ✓ Connected\nserena: command - ✓ Connected\n'
}

run_claude_version() {
  printf '2.1.241 (Claude Code)\n'
}

run_claude_latest_version() {
  printf '2.1.241\n'
}

run_headroom_runtime_flags() {
  printf '%s\n' 'HEADROOM_OUTPUT_SHAPER=1' 'HEADROOM_OUTPUT_HOLDOUT='
}

healthy_output="$TEST_OUTPUT_DIR/healthy"
WARNINGS=0
check_agent_harness > "$healthy_output"
[ "$WARNINGS" -eq 0 ] || fail "healthy harness produced $WARNINGS warning(s)"
assert_contains "2 MCP server(s) connected" "$healthy_output"
assert_contains "installed 2.1.241; latest stable 2.1.241" "$healthy_output"
assert_contains "output shaper flag reached the proxy" "$healthy_output"
assert_contains "no output holdout" "$healthy_output"

run_claude_mcp_list() {
  return 124
}

mcp_timeout_output="$TEST_OUTPUT_DIR/mcp-timeout"
WARNINGS=0
check_agent_harness > "$mcp_timeout_output"
[ "$WARNINGS" -eq 0 ] || fail "MCP timeout produced $WARNINGS warning(s), expected 0"
assert_contains "MCP status check timed out after 8s" "$mcp_timeout_output"
assert_contains "installed 2.1.241; latest stable 2.1.241" "$mcp_timeout_output"
osascript() { fail "temporary outage sent a notification"; }
NOTIFY=1 finish > "$TEST_OUTPUT_DIR/mcp-timeout-summary"
assert_contains "unverified" "$TEST_OUTPUT_DIR/mcp-timeout-summary"
assert_not_contains "all clear" "$TEST_OUTPUT_DIR/mcp-timeout-summary"
check_mcp_servers > "$TEST_OUTPUT_DIR/mcp-timeout-section"
assert_not_contains "[HEALTHY]" "$TEST_OUTPUT_DIR/mcp-timeout-section"

run_claude_mcp_list() {
  printf 'broken: missing-command - ✗ Failed: command not found\n'
}

mcp_invalid_output="$TEST_OUTPUT_DIR/mcp-invalid"
WARNINGS=0
check_mcp_servers > "$mcp_invalid_output"
[ "$WARNINGS" -eq 1 ] || fail "invalid MCP config produced $WARNINGS warning(s), expected 1"
assert_contains "MCP server 'broken' has a configuration error" "$mcp_invalid_output"

run_claude_mcp_list() {
  printf 'context7: command - ✓ Connected\nserena: command - ✓ Connected\n'
}

run_headroom_savings() {
  printf '%s\n' \
    '  Method:    ESTIMATED (synthetic control)' \
    '  Requests:  1,950 shaped' \
    '  Saved:     1,402,159 output tokens' \
    '  Reduction: 63.5%   (95% CI 12.9% … 114.2%)'
}

estimated_output="$TEST_OUTPUT_DIR/estimated-savings"
WARNINGS=0
check_headroom > "$estimated_output"
[ "$WARNINGS" -eq 0 ] || fail "estimated savings produced $WARNINGS warning(s)"
assert_contains "output shaper: ESTIMATED; 1,950 shaped; 1,402,159 output tokens; 63.5%" "$estimated_output"

run_headroom_savings() {
  printf '%s\n' \
    '  Method:    MEASURED' \
    '  Requests:  1,950 shaped' \
    '  Saved:     1,402,159 output tokens' \
    '  Reduction: 63.5%'
}

measured_output="$TEST_OUTPUT_DIR/measured-savings"
WARNINGS=0
check_headroom > "$measured_output"
[ "$WARNINGS" -eq 0 ] || fail "measured savings produced $WARNINGS warning(s)"
assert_contains "output shaper: MEASURED; 1,950 shaped" "$measured_output"

run_headroom_savings() {
  printf 'No shaped requests recorded yet.\n'
}

# A reachable proxy that is not shaping is the failure this check exists for.
run_headroom_runtime_flags() {
  printf '%s\n' 'HEADROOM_OUTPUT_SHAPER=' 'HEADROOM_OUTPUT_HOLDOUT='
}

shaper_off_output="$TEST_OUTPUT_DIR/shaper-off"
WARNINGS=0
check_headroom > "$shaper_off_output"
[ "$WARNINGS" -eq 1 ] || fail "shaper off produced $WARNINGS warning(s), expected 1"
assert_contains "output shaper is off" "$shaper_off_output"
assert_contains "install.sh --headroom-only" "$shaper_off_output"

# A configured holdout is what turns the reported savings into a measurement.
run_headroom_runtime_flags() {
  printf '%s\n' 'HEADROOM_OUTPUT_SHAPER=1' 'HEADROOM_OUTPUT_HOLDOUT=0.1'
}

holdout_output="$TEST_OUTPUT_DIR/holdout"
WARNINGS=0
check_headroom > "$holdout_output"
[ "$WARNINGS" -eq 0 ] || fail "configured holdout produced $WARNINGS warning(s)"
assert_contains "output holdout: 0.1" "$holdout_output"

# An unreadable /health must warn rather than claim the shaper is off.
run_headroom_runtime_flags() {
  return 1
}

flags_failed_output="$TEST_OUTPUT_DIR/flags-failed"
WARNINGS=0
check_headroom > "$flags_failed_output"
[ "$WARNINGS" -eq 1 ] || fail "unreadable flags produced $WARNINGS warning(s), expected 1"
assert_contains "runtime flags could not be read" "$flags_failed_output"
assert_not_contains "output shaper is off" "$flags_failed_output"

run_headroom_runtime_flags() {
  printf '%s\n' 'HEADROOM_OUTPUT_SHAPER=1' 'HEADROOM_OUTPUT_HOLDOUT='
}

run_headroom_status() {
  printf 'Status: stopped\nHealthy: yes\n'
}

temporary_proxy_output="$TEST_OUTPUT_DIR/temporary-proxy"
WARNINGS=0
check_headroom > "$temporary_proxy_output"
[ "$WARNINGS" -eq 1 ] || fail "temporary proxy conflict produced $WARNINGS warning(s), expected 1"
assert_contains "temporary proxy is reachable" "$temporary_proxy_output"
assert_contains "close headroom wrap sessions" "$temporary_proxy_output"

run_headroom_status() {
  printf 'Status: stopped\nHealthy: no\n'
}

run_claude_mcp_list() {
  printf '%s\n' \
    'context7: command - ✓ Connected' \
    'serena: command credential-do-not-log - ✗ Failed'
}

run_claude_version() {
  printf '2.1.231 (Claude Code)\n'
}

unhealthy_output="$TEST_OUTPUT_DIR/unhealthy"
WARNINGS=0
check_agent_harness > "$unhealthy_output"
[ "$WARNINGS" -eq 2 ] || fail "unhealthy harness produced $WARNINGS warning(s), expected 2"
assert_contains "run install.sh --headroom-only" "$unhealthy_output"
assert_contains "MCP server 'serena' is not connected (possibly temporary)" "$unhealthy_output"
assert_contains "Claude Code installed 2.1.231; latest stable 2.1.241" "$unhealthy_output"
assert_not_contains "credential-do-not-log" "$unhealthy_output"

run_claude_latest_version() { return 124; }
WARNINGS=0
UNVERIFIED=0
check_claude_version > "$TEST_OUTPUT_DIR/version-timeout"
[ "$WARNINGS" -eq 0 ] || fail "latest version timeout produced a warning"
[ "$UNVERIFIED" -eq 1 ] || fail "latest version timeout was not classified as unverified"
assert_contains "[UNVERIFIED]" "$TEST_OUTPUT_DIR/version-timeout"
assert_not_contains "[HEALTHY]" "$TEST_OUTPUT_DIR/version-timeout"

MEMORY_FIXTURE="$TEST_OUTPUT_DIR/memory"
mkdir -p "$MEMORY_FIXTURE"

agent_memory_dir() {
  printf '%s\n' "$MEMORY_FIXTURE"
}

write_memory() {
  local name="$1" body="$2"
  {
    printf -- '---\n'
    printf 'name: %s\n' "$name"
    printf 'metadata:\n'
    printf '%s' "$body"
    printf -- '---\n\n'
    printf 'A recorded correction.\n'
  } > "$MEMORY_FIXTURE/$name.md"
}

write_memory linked-feedback '  type: feedback
  promoted: CLAUDE.md
'
write_memory orphan-feedback '  type: feedback
'
write_memory declined-feedback '  type: feedback
  promoted: none
'
write_memory stale-feedback '  type: feedback
  promoted: claude/rules/common/deleted-rule.md
'
write_memory project-note '  type: project
'

memory_output="$TEST_OUTPUT_DIR/memory-promotion"
WARNINGS=0
check_memory_promotion > "$memory_output"
[ "$WARNINGS" -eq 2 ] || fail "memory fixture produced $WARNINGS warning(s), expected 2"
assert_contains "feedback not promoted: orphan-feedback" "$memory_output"
assert_contains "promotion target is missing: stale-feedback" "$memory_output"
assert_not_contains "linked-feedback" "$memory_output"
assert_not_contains "declined-feedback" "$memory_output"
assert_not_contains "project-note" "$memory_output"

# A body that quotes the frontmatter keys must not be read as frontmatter.
printf -- '---\nname: quoting-body\nmetadata:\n  type: reference\n---\n\n  type: feedback\n' \
  > "$MEMORY_FIXTURE/quoting-body.md"
quoting_output="$TEST_OUTPUT_DIR/memory-quoting"
WARNINGS=0
check_memory_promotion > "$quoting_output"
[ "$WARNINGS" -eq 2 ] || fail "quoted keys produced $WARNINGS warning(s), expected 2"
assert_not_contains "quoting-body" "$quoting_output"
rm "$MEMORY_FIXTURE/quoting-body.md"

# Claude Code owns the memory path, so a missing directory must not warn.
agent_memory_dir() {
  printf '%s\n' "$TEST_OUTPUT_DIR/absent-memory"
}

absent_output="$TEST_OUTPUT_DIR/memory-absent"
WARNINGS=0
check_memory_promotion > "$absent_output"
[ "$WARNINGS" -eq 0 ] || fail "absent memory directory produced $WARNINGS warning(s), expected 0"
assert_contains "no agent memory directory for this repository" "$absent_output"

SYNC_HOME="$TEST_OUTPUT_DIR/sync-home"
SYNC_REPO="$TEST_OUTPUT_DIR/sync-repo"
SYNC_BIN="$TEST_OUTPUT_DIR/sync-bin"
SUPPORTED_PYTHON=""
for candidate in python3 python3.13 python3.11; do
  if "$candidate" -c 'import sys, tomllib; sys.exit(sys.version_info < (3, 11))' > /dev/null 2>&1; then
    SUPPORTED_PYTHON=$(command -v "$candidate")
    break
  fi
done
[ -n "$SUPPORTED_PYTHON" ] || fail "doctor tests require Python 3.11+"
mkdir -p "$SYNC_HOME/.codex/dotfiles-sync" "$SYNC_REPO/scripts/codex-sync" "$SYNC_BIN"
: > "$SYNC_HOME/.codex/dotfiles-sync/state.json"
cat > "$SYNC_REPO/scripts/codex-sync/install.py" <<'PY'
import tomllib
print("sync fixture current")
PY
cat > "$SYNC_BIN/python3" <<'SH'
#!/bin/bash
if [ "$1" = -c ]; then
  exit 1
fi
printf "ModuleNotFoundError: No module named 'tomllib'\n" >&2
exit 1
SH
chmod +x "$SYNC_BIN/python3"

write_sync_python() {
  cat > "$SYNC_BIN/$1" <<SH
#!/bin/bash
exec "$SUPPORTED_PYTHON" "\$@"
SH
  chmod +x "$SYNC_BIN/$1"
}

run_sync_fixture() {
  local fixture_name="$1" expected_exit="$2"
  local fixture_exit=0
  env -i HOME="$SYNC_HOME" PATH=/usr/bin:/bin /bin/bash -c '
    source "$1"
    DOTFILES_DIR="$2"
    PATH="$3"
    check_codex_sync
    finish
  ' bash "$REPO_DIR/.shell-utils/dotfiles-doctor.sh" "$SYNC_REPO" "$SYNC_BIN" \
    > "$TEST_OUTPUT_DIR/$fixture_name" 2>&1 || fixture_exit=$?
  [ "$fixture_exit" -eq "$expected_exit" ] \
    || fail "$fixture_name returned $fixture_exit, expected $expected_exit"
}

write_sync_python python3.13
run_sync_fixture sync-compatible 0
assert_contains 'sync fixture current' "$TEST_OUTPUT_DIR/sync-compatible"
assert_not_contains 'ModuleNotFoundError' "$TEST_OUTPUT_DIR/sync-compatible"

rm "$SYNC_BIN/python3.13"
run_sync_fixture sync-unsupported 1
assert_contains 'Python 3.11+ is unavailable' "$TEST_OUTPUT_DIR/sync-unsupported"
assert_not_contains 'ModuleNotFoundError' "$TEST_OUTPUT_DIR/sync-unsupported"

rm "$SYNC_BIN/python3"
run_sync_fixture sync-python-missing 1
assert_contains 'Python is not installed' "$TEST_OUTPUT_DIR/sync-python-missing"

write_sync_python python3
cat > "$SYNC_REPO/scripts/codex-sync/install.py" <<'PY'
import tomllib
print("sync fixture drift")
raise SystemExit(1)
PY
run_sync_fixture sync-drift 1
assert_contains 'Codex sync needs attention: sync fixture drift' "$TEST_OUTPUT_DIR/sync-drift"

fixture_exit=0
env -i HOME="$SYNC_HOME" PATH=/usr/bin:/bin /bin/bash -c '
  source "$1"
  PATH="$2"
  check_agent_harness
  finish
' bash "$REPO_DIR/.shell-utils/dotfiles-doctor.sh" "$SYNC_BIN" \
  > "$TEST_OUTPUT_DIR/cli-missing" 2>&1 || fixture_exit=$?
[ "$fixture_exit" -eq 1 ] || fail "missing CLI returned $fixture_exit, expected 1"
assert_contains 'Headroom is not installed' "$TEST_OUTPUT_DIR/cli-missing"
assert_contains 'Claude Code is not installed' "$TEST_OUTPUT_DIR/cli-missing"

COMPACT_HOME="$TEST_OUTPUT_DIR/compact-home"
COMPACT_BIN="$TEST_OUTPUT_DIR/compact-bin"
COMPACT_TMP="$TEST_OUTPUT_DIR/compact-tmp"
mkdir -p "$COMPACT_HOME/.claude/hooks" "$COMPACT_BIN" "$COMPACT_TMP"
ln -s "$SUPPORTED_PYTHON" "$COMPACT_BIN/python3"
ln -s .claude "$COMPACT_HOME/claude"
printf 'raise RuntimeError("doctor must not execute the hook")\n' > "$COMPACT_HOME/.claude/hooks/compact-tool-output.py"

write_compaction_settings() {
  cat > "$COMPACT_HOME/.claude/settings.json" <<'JSON'
{"env":{"SECRET_TOKEN":"credential-do-not-log"},"hooks":{"PostToolUse":[{"matcher":"Read|Grep|Glob|WebFetch|WebSearch|mcp__.*","hooks":[{"type":"command","command":"python3 \"$HOME/.claude/hooks/compact-tool-output.py\"","timeout":10}]}]}}
JSON
}

run_compaction_fixture() {
  local fixture_name="$1" expected_exit="$2" fixture_exit=0
  env -i HOME="$COMPACT_HOME" PATH="$COMPACT_BIN:/usr/bin:/bin" TMPDIR="$COMPACT_TMP" \
    CLAUDE_TOOL_OUTPUT_CACHE_DIR="$COMPACT_HOME/real-cache" SECRET_TOKEN=credential-do-not-log \
    /bin/bash -c '
      source "$1"
      DOTFILES_DIR="$2"
      EXTERNAL_CHECK_TIMEOUT_SECONDS="$3"
      check_output_compaction
      finish
    ' bash "$REPO_DIR/.shell-utils/dotfiles-doctor.sh" "$COMPACT_HOME" "${3:-8}" \
    > "$TEST_OUTPUT_DIR/$fixture_name" 2>&1 || fixture_exit=$?
  [ "$fixture_exit" -eq "$expected_exit" ] \
    || fail "$fixture_name returned $fixture_exit, expected $expected_exit"
  assert_not_contains credential-do-not-log "$TEST_OUTPUT_DIR/$fixture_name"
  assert_not_contains "all clear" "$TEST_OUTPUT_DIR/$fixture_name"
  [ -z "$(ls -A "$COMPACT_TMP")" ] || fail "$fixture_name created temporary files"
}

write_compaction_settings
cp "$COMPACT_HOME/.claude/settings.json" "$TEST_OUTPUT_DIR/settings-original"
mkdir "$COMPACT_HOME/real-cache"
printf 'existing private archive\n' > "$COMPACT_HOME/real-cache/sentinel.json"
run_compaction_fixture compact-static 0
assert_contains "[HEALTHY] user compaction registration and script file (static only)" "$TEST_OUTPUT_DIR/compact-static"
assert_contains "[UNVERIFIED] compaction behavior and effective Claude hook invocation" "$TEST_OUTPUT_DIR/compact-static"
assert_contains "test_compact_tool_output.py" "$TEST_OUTPUT_DIR/compact-static"
assert_not_contains "synthetic" "$TEST_OUTPUT_DIR/compact-static"
cmp "$COMPACT_HOME/.claude/settings.json" "$TEST_OUTPUT_DIR/settings-original" || fail "inspection changed user settings"
assert_contains "existing private archive" "$COMPACT_HOME/real-cache/sentinel.json"
[ "$(ls -A "$COMPACT_HOME/real-cache")" = sentinel.json ] || fail "inspection wrote to the real cache"

rm "$COMPACT_HOME/.claude/settings.json"
run_compaction_fixture compact-unused 0
assert_contains "[NOT APPLICABLE] no user compaction registration" "$TEST_OUTPUT_DIR/compact-unused"

printf '{"secret":"credential-do-not-log"\n' > "$COMPACT_HOME/.claude/settings.json"
run_compaction_fixture compact-invalid-settings 1
assert_contains "[ABNORMAL] WARN: user hook settings are invalid" "$TEST_OUTPUT_DIR/compact-invalid-settings"

printf '{"hooks":{"PostToolUse":[{"hooks":{}}]}}\n' > "$COMPACT_HOME/.claude/settings.json"
run_compaction_fixture compact-invalid-schema 1
assert_contains "user hook settings are invalid" "$TEST_OUTPUT_DIR/compact-invalid-schema"

rm "$COMPACT_HOME/.claude/settings.json"
mkdir "$COMPACT_HOME/.claude/settings.json"
run_compaction_fixture compact-unreadable-settings 0
assert_contains "[UNVERIFIED] user hook settings could not be read" "$TEST_OUTPUT_DIR/compact-unreadable-settings"
rmdir "$COMPACT_HOME/.claude/settings.json"

mkfifo "$COMPACT_HOME/.claude/settings.json"
run_compaction_fixture compact-read-timeout 0 0.1
assert_contains "[UNVERIFIED] compaction inspection could not run" "$TEST_OUTPUT_DIR/compact-read-timeout"
rm "$COMPACT_HOME/.claude/settings.json"

printf '{"disableAllHooks":true,"hooks":{}}\n' > "$COMPACT_HOME/.claude/settings.json"
run_compaction_fixture compact-disabled 0
assert_contains "[NOT APPLICABLE] user hooks are disabled" "$TEST_OUTPUT_DIR/compact-disabled"

cat > "$COMPACT_HOME/.claude/settings.json" <<'JSON'
{"hooks":{"PostToolUse":[{"hooks":[{"type":"command","command":"python3 \"$HOME/.claude/hooks/compact-tool-output.py\"; touch \"$HOME/unexpected-execution\""}]}]}}
JSON
run_compaction_fixture compact-custom-command 0
assert_contains "[UNVERIFIED] custom compaction registration" "$TEST_OUTPUT_DIR/compact-custom-command"
[ ! -e "$COMPACT_HOME/unexpected-execution" ] || fail "doctor executed a custom command"

write_compaction_settings
rm "$COMPACT_HOME/.claude/hooks/compact-tool-output.py"
run_compaction_fixture compact-missing 1
assert_contains "[ABNORMAL] WARN: registered compaction script is missing" "$TEST_OUTPUT_DIR/compact-missing"
assert_not_contains "[HEALTHY]" "$TEST_OUTPUT_DIR/compact-missing"

printf 'dotfiles-doctor tests: ok\n'
