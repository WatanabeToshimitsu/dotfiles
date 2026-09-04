#!/usr/bin/env bash

# Read JSON input from stdin
input=$(cat)

MESSAGE=$(echo "$input" | jq -r '.message')

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

# Pushover is opt-in because the notification body is sent to an external API.
if [ -z "${PUSHOVER_API_TOKEN:-}" ] || [ -z "${PUSHOVER_USER_KEY:-}" ]; then
  exit 0
fi

curl --silent --show-error \
    --connect-timeout 3 \
    --max-time 5 \
    --form-string "token=${PUSHOVER_API_TOKEN}" \
    --form-string "user=${PUSHOVER_USER_KEY}" \
    --form-string "message=${NOTIFY_MSG}" \
    --form-string "device=iphone15" \
    --form-string "title=Claude Code" \
    https://api.pushover.net/1/messages.json \
    > /dev/null 2>&1 || :
