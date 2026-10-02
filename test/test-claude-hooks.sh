#!/usr/bin/env bash
set -uo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="$(cd "$TEST_DIR/../claude/hooks" && pwd)"

FAILURES=0

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  FAILURES=$((FAILURES + 1))
}

# A hook that permits the call stays silent, so no output means allow.
decision_for() {
  local hook="$1" payload="$2" output
  output=$(printf '%s' "$payload" | bash "$HOOKS_DIR/$hook" 2> /dev/null)
  if [ -z "$output" ]; then
    printf 'allow\n'
  else
    printf '%s' "$output" | jq -r '.hookSpecificOutput.permissionDecision // "unparsed"'
  fi
}

expect_decision() {
  local hook="$1" payload="$2" expected="$3" label="$4" actual reason
  actual=$(decision_for "$hook" "$payload")
  [ "$actual" = "$expected" ] || fail "$hook: $label expected $expected, got $actual"
  if [ "$#" -eq 5 ]; then
    reason=$(printf '%s' "$payload" | bash "$HOOKS_DIR/$hook" | jq -r '.hookSpecificOutput.permissionDecisionReason')
    [ "$reason" = "$5" ] || fail "$hook: $label returned obsolete model-role guidance"
  fi
}

expect_exit() {
  local hook="$1" payload="$2" expected="$3" label="$4" actual
  printf '%s' "$payload" | bash "$HOOKS_DIR/$hook" > /dev/null 2>&1
  actual=$?
  [ "$actual" -eq "$expected" ] || fail "$hook: $label expected exit $expected, got $actual"
}

expect_nonzero_exit() {
  local hook="$1" payload="$2" label="$3" actual
  printf '%s' "$payload" | bash "$HOOKS_DIR/$hook" > /dev/null 2>&1
  actual=$?
  [ "$actual" -ne 0 ] || fail "$hook: $label expected a non-zero exit, got 0"
}

bash_payload() {
  jq -n --arg command "$1" '{tool_name: "Bash", tool_input: {command: $command}}'
}

agent_payload() {
  jq -n --arg subagent_type "$1" --arg model "$2" \
    '{tool_name: "Agent", tool_input: {subagent_type: $subagent_type, model: $model}}'
}

expect_decision validate-bash.sh "$(bash_payload 'git -C fixture add -A')" deny "the -A flag with -C"
expect_decision validate-bash.sh "$(bash_payload 'git --no-optional-locks add --all')" deny "the --all flag with global options"
expect_decision validate-bash.sh "$(bash_payload 'rtk proxy git -C fixture add .')" deny "a bare dot through RTK"
expect_decision validate-bash.sh "$(bash_payload 'rtk git -Cfixture -C sub --no-optional-locks add . ; git status')" deny "a scoped dot before a separator"
expect_decision validate-bash.sh "$(bash_payload 'git -C fixture add -- -A')" allow "a named path after --"
expect_decision validate-bash.sh "$(bash_payload 'rtk proxy git --no-optional-locks -C fixture add ./src/main.ts')" allow "a relative path through RTK"
expect_decision validate-bash.sh "$(bash_payload 'git commit -m x')" allow "an unrelated command"
expect_decision validate-bash.sh '{"tool_name":"Read","tool_input":{}}' allow "a non-Bash tool"

# Malformed input leaves the call permitted. This hook guards a personal
# convention rather than a security boundary, so it fails open on purpose.
expect_decision validate-bash.sh 'not json' allow "malformed input"
expect_exit validate-bash.sh 'not json' 0 "malformed input"

expect_decision require-subagent-model.sh "$(agent_payload general-purpose sonnet)" allow "an explicit model"
expect_decision require-subagent-model.sh "$(agent_payload general-purpose inherit)" deny "an inherited model" \
  'Specify an explicit non-inherit model for every subagent. Follow delivery-workflow for role selection and independent review.'
expect_decision require-subagent-model.sh "$(agent_payload general-purpose '')" deny "a missing model" \
  'Specify an explicit non-inherit model for every subagent. Follow delivery-workflow for role selection and independent review.'
expect_decision require-subagent-model.sh "$(agent_payload sonnet-worker '')" allow "a pinned subagent type"
expect_decision require-subagent-model.sh "$(agent_payload fable-deep '')" allow "a pinned subagent type"
expect_decision require-subagent-model.sh '{"tool_name":"Read","tool_input":{}}' allow "a non-Agent tool"

# This hook runs under `set -e`, so malformed input aborts instead of denying.
# The exact status comes from jq and is not asserted.
expect_decision require-subagent-model.sh 'not json' allow "malformed input"
expect_nonzero_exit require-subagent-model.sh 'not json' "malformed input"

if [ "$FAILURES" -ne 0 ]; then
  printf 'claude hook tests: %d failure(s)\n' "$FAILURES" >&2
  exit 1
fi

printf 'claude hook tests: ok\n'
