#!/usr/bin/env bash
# Integration test for install.sh
set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ERRORS=0

echo "=== Syntax check ==="
bash -n "$DOTFILES_DIR/install.sh" || { echo "FAIL: install.sh syntax error"; ERRORS=$((ERRORS + 1)); }

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

echo ""
if [ "$ERRORS" -eq 0 ]; then
    echo "All tests passed!"
else
    echo "FAILED: $ERRORS error(s)"
    exit 1
fi
