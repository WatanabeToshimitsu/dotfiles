#!/bin/bash
# Validate specific Bash commands usage

# Read JSON input from stdin
input=$(cat)

if ! jq -e . > /dev/null 2>&1 <<< "$input"; then
  exit 0
fi

tool_name=$(jq -r '.tool_name // ""' <<< "$input")
command=$(jq -r '.tool_input.command // ""' <<< "$input")

# Only validate Bash tool
if [[ "$tool_name" != "Bash" ]]; then
  exit 0
fi

# Deny with JSON hookSpecificOutput
deny() {
  jq -n --arg reason "$1" '{
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "deny",
      "permissionDecisionReason": $reason
    }
  }'
  exit 0
}

if echo "$command" | grep -qE '\bgit add (-A|--all|\.($|[ ;|&]))'; then
  deny "Do not git-add all files. Specify the file name(s) to add."
fi

exit 0
