#!/usr/bin/env bash
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$TEST_DIR/.." && pwd)"
TEST_ROOT=$(mktemp -d)
trap 'rm -rf "$TEST_ROOT"' EXIT

claude_version=$(jq -r '.claudeCode' "$REPO_DIR/claude/dependencies.lock.json")
claude_package="@anthropic-ai/claude-code@$claude_version"
diagnostic="$TEST_ROOT/doctor.log"

if ! npx -y "$claude_package" --settings "$REPO_DIR/claude/settings.json" doctor \
  > "$diagnostic" 2>&1; then
  cat "$diagnostic" >&2
  exit 1
fi

if grep -Eq 'Invalid settings|Settings Error' "$diagnostic"; then
  cat "$diagnostic" >&2
  exit 1
fi

printf 'Claude settings tests: ok\n'
