#!/bin/bash
# Remove dotfiles symlinks created by install.sh.
# Only removes symlinks that resolve into this repo; real files and
# foreign symlinks are left untouched. Backups (if any) are never restored
# automatically; restore manually from ~/.dotfiles-backup.
set -uo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

# shellcheck source=symlink-manifest.sh
source "$DOTFILES_DIR/symlink-manifest.sh"

# Remove a symlink only if it points into this dotfiles repo.
remove_if_dotfiles_symlink() {
  local target=$1
  [ -L "$target" ] || return 0

  local link_target
  link_target=$(readlink "$target")
  case "$link_target" in
    "$DOTFILES_DIR"/*) ;;
    *) return 0 ;;
  esac

  if [ "$DRY_RUN" -eq 1 ]; then
    echo "  would remove: $target"
  else
    rm -f "$target"
    echo "  removed: $target"
  fi
}

echo "----------------------------------------------"
echo "Removing dotfiles symlinks..."
echo "----------------------------------------------"

for file in "${MANIFEST_FILES[@]}"; do
  remove_if_dotfiles_symlink "$HOME/$file"
done

for file in "${MANIFEST_CONFIG_FILES[@]}"; do
  remove_if_dotfiles_symlink "$HOME/$file"
done

for file in "${MANIFEST_CLAUDE_FILES[@]}"; do
  remove_if_dotfiles_symlink "$HOME/.claude/$file"
done

remove_if_dotfiles_symlink "$HOME/.shell-utils"
remove_if_dotfiles_symlink "$HOME/oh-my-posh-theme"

if [ "$(uname -s)" = "Darwin" ]; then
  remove_if_dotfiles_symlink "$HOME/Library/Application Support/Code/User/keybindings.json"
fi

if [ -d "$HOME/.dotfiles-backup" ]; then
  latest_backup=""
  for dir in "$HOME/.dotfiles-backup"/*/; do
    [ -d "$dir" ] && latest_backup="$dir"
  done

  if [ -n "$latest_backup" ]; then
    echo ""
    echo "Backups found. Newest: $latest_backup"
    echo "Restore any files you need manually from there."
  fi
fi
