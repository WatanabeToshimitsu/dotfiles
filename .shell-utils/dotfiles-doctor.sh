#!/usr/bin/env bash
# dotfiles-doctor: report drift between this repo and the machine.
# Checks: broken symlinks, Brewfile coverage, agent-skill coverage, dirty repo.
set -uo pipefail

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WARNINGS=0

warn() {
  printf '  WARN: %s\n' "$*"
  WARNINGS=$((WARNINGS + 1))
}

section_ok() {
  [ "$WARNINGS" -eq "$1" ] && printf '  ok\n'
}

echo "== broken symlinks (~/, ~/.config, ~/.claude, VS Code) =="
before=$WARNINGS
while IFS= read -r link; do
  warn "broken symlink: $link"
done < <(
  find "$HOME" -maxdepth 1 -name ".*" -type l ! -exec test -e {} \; -print 2>/dev/null
  find "$HOME/.config" "$HOME/.claude" "$HOME/Library/Application Support/Code/User" \
    -maxdepth 3 -type l ! -exec test -e {} \; -print 2>/dev/null
)
section_ok "$before"

echo "== brew leaves not in Brewfile =="
before=$WARNINGS
if command -v brew > /dev/null 2>&1; then
  while IFS= read -r formula; do
    [ -n "$formula" ] && warn "installed but untracked: $formula"
  done < <(comm -23 <(brew leaves | sort) \
    <(grep '^brew "' "$DOTFILES_DIR/Brewfile" | perl -pe 's/^brew "([^"]+)".*/$1/; s|.*/||' | sort))
fi
section_ok "$before"

echo "== agent skills not restored by install.sh =="
before=$WARNINGS
for dir in "$HOME/.agents/skills"/*/; do
  [ -d "$dir" ] || continue
  name=$(basename "$dir")
  grep -q ":${name}\"" "$DOTFILES_DIR/install.sh" ||
    warn "skill not in setup_agent_skills: $name"
done
section_ok "$before"

echo "== dotfiles repo state =="
before=$WARNINGS
if git -C "$DOTFILES_DIR" status --porcelain 2>/dev/null | grep -q .; then
  warn "uncommitted changes in $DOTFILES_DIR"
fi
if [ -n "$(git -C "$DOTFILES_DIR" log --oneline '@{upstream}..HEAD' 2>/dev/null)" ]; then
  warn "unpushed commits in $DOTFILES_DIR"
fi
section_ok "$before"

echo
if [ "$WARNINGS" -eq 0 ]; then
  echo "doctor: all clear"
else
  echo "doctor: $WARNINGS warning(s)"
  exit 1
fi
