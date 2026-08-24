#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
file="$(jq -r '.tool_input.file_path // .tool_input.path // empty' <<< "$input")"
cwd="$(jq -r '.cwd // empty' <<< "$input")"

case "$file" in
  *.ts|*.tsx|*.js|*.jsx) ;;
  *) exit 0 ;;
esac

[ -n "$cwd" ] || exit 0
project_root="$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null)" || exit 0
oxlint="$project_root/node_modules/.bin/oxlint"
[ -x "$oxlint" ] || exit 0

case "$file" in
  /*) ;;
  *) file="$cwd/$file" ;;
esac

diag="$({ "$oxlint" "$file" 2>&1 || true; } | head -20)"

if [ -n "$diag" ]; then
  jq -Rn --arg msg "$diag" '{
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      additionalContext: $msg
    }
  }'
fi
