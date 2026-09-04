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

has_command() {
  return 0
}

headroom_deployment_configured() {
  return 0
}

compactor_hook_configured() {
  return 0
}

run_headroom_status() {
  printf 'Status: running\nHealthy: yes\n'
}

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

run_compactor_health() {
  printf '%s\n' \
    'window: 7 days' \
    'hook active: yes' \
    'hook last invoked: 2026-08-26T00:00:00Z' \
    'hook last error: none'
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
assert_contains "hook active; last invoked 2026-08-26T00:00:00Z" "$healthy_output"
assert_contains "output shaper flag reached the proxy" "$healthy_output"
assert_contains "no output holdout" "$healthy_output"

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

run_compactor_health() {
  printf '%s\n' \
    'window: 7 days' \
    'hook active: no' \
    'hook last invoked: never' \
    'hook last error: JSONDecodeError at 2026-08-26T00:00:00Z'
}

unhealthy_output="$TEST_OUTPUT_DIR/unhealthy"
WARNINGS=0
check_agent_harness > "$unhealthy_output"
[ "$WARNINGS" -eq 5 ] || fail "unhealthy harness produced $WARNINGS warning(s), expected 5"
assert_contains "run install.sh --headroom-only" "$unhealthy_output"
assert_contains "MCP server 'serena' is not connected" "$unhealthy_output"
assert_contains "Claude Code installed 2.1.231; latest stable 2.1.241" "$unhealthy_output"
assert_contains "Compaction hook was not observed in 7 days" "$unhealthy_output"
assert_contains "unresolved JSONDecodeError" "$unhealthy_output"
assert_not_contains "credential-do-not-log" "$unhealthy_output"

printf 'dotfiles-doctor tests: ok\n'
