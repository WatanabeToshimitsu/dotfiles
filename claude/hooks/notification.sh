#!/usr/bin/env bash

# Read JSON input from stdin
input=$(cat)

if ! jq -e . > /dev/null 2>&1 <<< "$input"; then
  exit 0
fi

MESSAGE=$(jq -r '.message // empty' <<< "$input")
[ -n "$MESSAGE" ] || exit 0

case "$MESSAGE" in
  'Claude is waiting for your input')
    NOTIFY_MSG="Claudeはあなたの入力を待っています"
    ;;
  'Claude Code login successful')
    # do nothing
    exit 0
    ;;
  'Claude needs your permission to use '*)
    NOTIFY_MSG="${MESSAGE#Claude needs your permission to use }の許可が必要です"
    ;;
  *)
    NOTIFY_MSG="${MESSAGE}"
    ;;
esac

# osascript -e "display notification \"${NOTIFY_MSG}\" with title \"Claude Code\" sound name \"Glass\""

# Pushover notification
[ -n "${PUSHOVER_API_TOKEN:-}" ] || exit 0
[ -n "${PUSHOVER_USER_KEY:-}" ] || exit 0

curl -s \
    --form-string "token=${PUSHOVER_API_TOKEN}" \
    --form-string "user=${PUSHOVER_USER_KEY}" \
    --form-string "message=${NOTIFY_MSG}" \
    --form-string "device=iphone15" \
    --form-string "title=Claude Code" \
    https://api.pushover.net/1/messages.json > /dev/null 2>&1 || :
