#!/usr/bin/env bash
# Integration test for install.sh
set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ERRORS=0

echo "=== Syntax check ==="
bash -n "$DOTFILES_DIR/install.sh" || { echo "FAIL: install.sh syntax error"; ERRORS=$((ERRORS + 1)); }
bash -n "$DOTFILES_DIR/uninstall.sh" || { echo "FAIL: uninstall.sh syntax error"; ERRORS=$((ERRORS + 1)); }

echo "=== Pre-creating a real .npmrc (to verify backup-before-symlink) ==="
NPMRC_CONTENT="pre-existing npmrc content"
echo "$NPMRC_CONTENT" > "$HOME/.npmrc"

echo "=== Running install.sh ==="
bash "$DOTFILES_DIR/install.sh"

echo "=== Verifying symlinks ==="
EXPECTED_LINKS=(
    "$HOME/.zshrc"
    "$HOME/.bashrc"
    "$HOME/.bash_profile"
    "$HOME/.profile"
    "$HOME/.vimrc"
    "$HOME/.tmux.conf"
)

for link in "${EXPECTED_LINKS[@]}"; do
    if [ -L "$link" ]; then
        echo "  OK: $link"
    else
        echo "  FAIL: $link is not a symlink"
        ERRORS=$((ERRORS + 1))
    fi
done

echo "=== Directory symlinks ==="
for dir_link in "$HOME/.shell-utils" "$HOME/oh-my-posh-theme"; do
    if [ -L "$dir_link" ]; then
        echo "  OK: $dir_link"
    else
        echo "  FAIL: $dir_link is not a symlink"
        ERRORS=$((ERRORS + 1))
    fi
done

echo "=== Verifying .npmrc was backed up before symlinking ==="
if [ -L "$HOME/.npmrc" ]; then
    echo "  OK: $HOME/.npmrc is now a symlink"
else
    echo "  FAIL: $HOME/.npmrc is not a symlink"
    ERRORS=$((ERRORS + 1))
fi

BACKED_UP_NPMRC=""
for candidate in "$HOME"/.dotfiles-backup/*/.npmrc; do
    [ -f "$candidate" ] && BACKED_UP_NPMRC="$candidate"
done

if [ -n "$BACKED_UP_NPMRC" ] && grep -q "$NPMRC_CONTENT" "$BACKED_UP_NPMRC"; then
    echo "  OK: backup found at $BACKED_UP_NPMRC"
else
    echo "  FAIL: no backup of the pre-existing .npmrc found under ~/.dotfiles-backup"
    ERRORS=$((ERRORS + 1))
fi

echo "=== Creating a foreign symlink (must survive uninstall) ==="
ln -sf /etc/hosts "$HOME/.foreign"

echo "=== Running uninstall.sh ==="
bash "$DOTFILES_DIR/uninstall.sh"

echo "=== Verifying tracked symlinks were removed ==="
for link in "$HOME/.zshrc" "$HOME/.vimrc"; do
    if [ ! -e "$link" ] && [ ! -L "$link" ]; then
        echo "  OK: $link removed"
    else
        echo "  FAIL: $link still present"
        ERRORS=$((ERRORS + 1))
    fi
done

if [ ! -e "$HOME/.shell-utils" ] && [ ! -L "$HOME/.shell-utils" ]; then
    echo "  OK: $HOME/.shell-utils removed"
else
    echo "  FAIL: $HOME/.shell-utils still present"
    ERRORS=$((ERRORS + 1))
fi

echo "=== Verifying the foreign symlink was left untouched ==="
if [ -L "$HOME/.foreign" ]; then
    echo "  OK: $HOME/.foreign still present"
else
    echo "  FAIL: $HOME/.foreign was removed"
    ERRORS=$((ERRORS + 1))
fi

echo ""
if [ "$ERRORS" -eq 0 ]; then
    echo "All tests passed!"
else
    echo "FAILED: $ERRORS error(s)"
    exit 1
fi
