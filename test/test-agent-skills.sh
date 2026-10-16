#!/usr/bin/env bash
# Tests that install.sh installs external agent skills for Claude Code and Codex
# without deleting a skill directory that already exists on one side.
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$TEST_DIR/.." && pwd)"

# shellcheck source=../install.sh
source "$REPO_DIR/install.sh" > /dev/null

SANDBOX=$(mktemp -d)
trap 'rm -rf "$SANDBOX"' EXIT

HOME="$SANDBOX/home"
DOTFILES_DIR="$SANDBOX/dotfiles"
NPX_LOG="$SANDBOX/npx.log"
mkdir -p "$HOME" "$DOTFILES_DIR"

npx() {
  printf '%s\n' "$*" >> "$NPX_LOG"
}

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

reset_case() {
  rm -rf "$HOME/.agents" "$HOME/.claude"
  : > "$NPX_LOG"
  printf 'owner/repo:%s\n' "$1" > "$DOTFILES_DIR/agent-skills.txt"
}

echo "=== A skill missing on both sides is installed for both clients ==="
reset_case fresh-skill
setup_agent_skills > "$SANDBOX/out" 2>&1
[ "$(wc -l < "$NPX_LOG")" -eq 1 ] || fail "expected one skills CLI call, got: $(cat "$NPX_LOG")"
grep -Fqx -- "-y skills add owner/repo -g -y -s fresh-skill -a claude-code -a codex" "$NPX_LOG" \
  || fail "skills CLI was not asked to target both clients: $(cat "$NPX_LOG")"

echo "=== A skill present on both sides is left alone ==="
reset_case shared-skill
mkdir -p "$HOME/.agents/skills/shared-skill" "$HOME/.claude/skills"
ln -s ../../.agents/skills/shared-skill "$HOME/.claude/skills/shared-skill"
setup_agent_skills > "$SANDBOX/out" 2>&1
[ ! -s "$NPX_LOG" ] || fail "skills CLI ran for an installed skill: $(cat "$NPX_LOG")"
grep -Fq "exists: shared-skill" "$SANDBOX/out" || fail "installed skill was not reported as existing"

for side in .claude .agents; do
  echo "=== A real copy only in ~/$side/skills is reported and never replaced ==="
  reset_case one-side
  mkdir -p "$HOME/$side/skills/one-side/reports"
  printf 'local report\n' > "$HOME/$side/skills/one-side/reports/r.md"
  setup_agent_skills > "$SANDBOX/out" 2>&1
  [ ! -s "$NPX_LOG" ] || fail "skills CLI ran over a ~/$side copy: $(cat "$NPX_LOG")"
  grep -Fq "partial: one-side" "$SANDBOX/out" || fail "partial install was not reported: $(cat "$SANDBOX/out")"
  [ "$(cat "$HOME/$side/skills/one-side/reports/r.md")" = "local report" ] \
    || fail "the ~/$side copy was modified"

  echo "=== A dangling link only in ~/$side/skills is reported and kept ==="
  reset_case dangling
  mkdir -p "$HOME/$side/skills"
  ln -s ../missing "$HOME/$side/skills/dangling"
  setup_agent_skills > "$SANDBOX/out" 2>&1
  [ ! -s "$NPX_LOG" ] || fail "skills CLI ran over a dangling ~/$side link: $(cat "$NPX_LOG")"
  grep -Fq "partial: dangling" "$SANDBOX/out" || fail "dangling link was not reported: $(cat "$SANDBOX/out")"
  [ "$(readlink "$HOME/$side/skills/dangling")" = "../missing" ] || fail "the dangling ~/$side link was changed"
done

echo "agent skill installation tests: ok"
