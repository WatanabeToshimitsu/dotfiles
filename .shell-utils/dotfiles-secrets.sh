#!/usr/bin/env bash
set -euo pipefail

umask 077

DOTFILES_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
TEMPLATE="$DOTFILES_DIR/templates/zshrc.local.tpl"
TARGET="$HOME/.zshrc.local"
FORCE=0

case "${1:-}" in
  "") ;;
  --force) FORCE=1 ;;
  *)
    echo "usage: dotfiles-secrets.sh [--force]" >&2
    exit 2
    ;;
esac

if ! command -v op > /dev/null 2>&1; then
  echo "error: 1Password CLI (op) not found; install it first" >&2
  exit 1
fi

if [ ! -f "$TEMPLATE" ]; then
  echo "error: template not found: $TEMPLATE" >&2
  exit 1
fi

if [ -d "$TARGET" ]; then
  echo "error: $TARGET is a directory; refusing to replace it" >&2
  exit 1
fi

if { [ -e "$TARGET" ] || [ -L "$TARGET" ]; } && [ "$FORCE" -ne 1 ]; then
  echo "error: $TARGET already exists; re-run with --force to overwrite" >&2
  exit 1
fi

if ! op account get > /dev/null 2>&1; then
  echo "error: not signed in to 1Password CLI; run: eval \"\$(op signin)\"" >&2
  exit 1
fi

TEMP_OUTPUT="$(mktemp "$(dirname "$TARGET")/.zshrc.local.XXXXXX")"
cleanup() {
  rm -f "$TEMP_OUTPUT"
}
trap cleanup EXIT HUP INT TERM

if ! op inject -f -i "$TEMPLATE" -o "$TEMP_OUTPUT"; then
  echo "error: 1Password failed to render $TEMPLATE" >&2
  exit 1
fi
chmod 600 "$TEMP_OUTPUT"

if [ "$FORCE" -eq 1 ]; then
  mv -f "$TEMP_OUTPUT" "$TARGET"
else
  mv -n "$TEMP_OUTPUT" "$TARGET"
  if [ -e "$TEMP_OUTPUT" ]; then
    echo "error: $TARGET was created while secrets were rendering; left it unchanged" >&2
    exit 1
  fi
fi
trap - EXIT HUP INT TERM

echo "rendered $TARGET from $TEMPLATE"
