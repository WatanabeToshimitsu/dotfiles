#!/usr/bin/env bash
# dotfiles-secrets: render ~/.zshrc.local from templates/zshrc.local.tpl via `op inject`.
# Requires the 1Password CLI (`op`) signed in. --force overwrites an existing ~/.zshrc.local.
set -uo pipefail

# -P resolves ~/.shell-utils (a symlink) so the parent is the real repo
DOTFILES_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
TEMPLATE="$DOTFILES_DIR/templates/zshrc.local.tpl"
TARGET="$HOME/.zshrc.local"
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

if ! command -v op > /dev/null 2>&1; then
  echo "error: 1Password CLI (op) not found; install it first" >&2
  exit 1
fi

if [ ! -f "$TEMPLATE" ]; then
  echo "error: template not found: $TEMPLATE" >&2
  exit 1
fi

if [ -e "$TARGET" ] && [ "$FORCE" -ne 1 ]; then
  echo "error: $TARGET already exists; re-run with --force to overwrite" >&2
  exit 1
fi

if ! op account get > /dev/null 2>&1; then
  echo "error: not signed in to 1Password CLI; run: eval \"\$(op signin)\"" >&2
  exit 1
fi

if [ "$FORCE" -eq 1 ]; then
  op inject -f -i "$TEMPLATE" -o "$TARGET"
else
  op inject -i "$TEMPLATE" -o "$TARGET"
fi
chmod 600 "$TARGET"
echo "rendered $TARGET from $TEMPLATE"
