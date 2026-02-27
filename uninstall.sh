#!/usr/bin/env bash
# Uninstall dotfiles: remove symlinks and optionally restore backups
set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"
DRY_RUN=false

log_info()  { echo "[INFO]  $*"; }
log_warn()  { echo "[WARN]  $*" >&2; }

usage() {
  echo "Usage: $0 [--dry-run]"
  echo "  --dry-run  Show what would be removed without making changes"
  exit 0
}

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --help|-h) usage ;;
    *) echo "Unknown option: $arg"; usage ;;
  esac
done

remove_symlink() {
  local link="$1"
  if [ -L "$link" ]; then
    local target
    target=$(readlink "$link")
    # Only remove if it points to our dotfiles directory
    case "$target" in
      "$DOTFILES_DIR"*)
        if $DRY_RUN; then
          log_info "[DRY-RUN] Would remove: $link -> $target"
        else
          rm "$link"
          log_info "Removed: $link"
        fi
        ;;
      *)
        log_warn "Skipping $link (points to $target, not our dotfiles)"
        ;;
    esac
  fi
}

echo "Uninstalling dotfiles from $DOTFILES_DIR"
if $DRY_RUN; then
  echo "(Dry run mode - no changes will be made)"
fi
echo ""

# File symlinks
FILES=(
  .zshrc .bashrc .bash_profile .bash_logout
  .profile .zprofile .zshenv
  .vimrc .tmux.conf .gitconfig
  .huskyrc .npmrc
)

for file in "${FILES[@]}"; do
  remove_symlink "$HOME/$file"
done

# .config/ files
CONFIG_FILES=(
  .config/git/ignore
  .config/gh/config.yml
  .config/ghostty/config
)

for file in "${CONFIG_FILES[@]}"; do
  remove_symlink "$HOME/$file"
done

# Claude Code files
CLAUDE_FILES=(
  CLAUDE.md RTK.md settings.json statusline.sh
  hooks/deny-check.sh hooks/notification.sh hooks/rtk-rewrite.sh hooks/validate-bash.sh
  rules/testing/vitest.md rules/typescript/documentation.md rules/typescript/type-safety.md
)

for file in "${CLAUDE_FILES[@]}"; do
  remove_symlink "$HOME/.claude/$file"
done

# Directory symlinks
remove_symlink "$HOME/.shell-utils"
remove_symlink "$HOME/oh-my-posh-theme"

# Offer backup restore
BACKUP_DIR="$HOME/.dotfiles-backup"
if [ -d "$BACKUP_DIR" ]; then
  echo ""
  echo "Backups found in $BACKUP_DIR:"
  ls -1 "$BACKUP_DIR"
  echo ""
  echo "To restore a backup, copy files from the backup directory to your home directory."
  echo "Example: cp -r $BACKUP_DIR/<timestamp>/* ~/"
fi

echo ""
echo "Uninstall complete!"
