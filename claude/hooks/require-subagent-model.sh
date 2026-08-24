#!/usr/bin/env bash
set -euo pipefail

input=$(cat)
tool_name=$(jq -r '.tool_name // ""' <<<"$input")

if [[ "$tool_name" != "Agent" ]]; then
  exit 0
fi

model=$(jq -r '.tool_input.model // ""' <<<"$input")

if [[ -n "$model" && "$model" != "inherit" ]]; then
  exit 0
fi

jq -n '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: "Specify an explicit non-inherit model for every subagent. Use sonnet for implementation, exploration, and routine review; use fable or opus only for high-risk design or adversarial review."
  }
}'
