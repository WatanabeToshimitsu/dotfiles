#!/usr/bin/env bash
# Integration test for install.sh
set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ERRORS=0

# shellcheck source=../symlink-manifest.sh
source "$DOTFILES_DIR/symlink-manifest.sh"

echo "=== Syntax check ==="
bash -n "$DOTFILES_DIR/install.sh" || { echo "FAIL: install.sh syntax error"; ERRORS=$((ERRORS + 1)); }
bash -n "$DOTFILES_DIR/uninstall.sh" || { echo "FAIL: uninstall.sh syntax error"; ERRORS=$((ERRORS + 1)); }

echo "=== Pre-creating a machine-local .npmrc ==="
NPMRC_CONTENT="pre-existing npmrc content"
echo "$NPMRC_CONTENT" > "$HOME/.npmrc"

echo "=== Pre-creating retired Claude hook symlinks ==="
mkdir -p "$HOME/.claude/hooks"
ln -s "$DOTFILES_DIR/claude/hooks/deny-check.sh" "$HOME/.claude/hooks/deny-check.sh"
ln -s "$DOTFILES_DIR/claude/hooks/link-worktree-memory.sh" "$HOME/.claude/hooks/link-worktree-memory.sh"

echo "=== Pre-creating real directories that install.sh must not delete ==="
SENTINEL_CONTENT="machine-local file that predates the symlink"
for real_dir in "$HOME/.shell-utils" "$HOME/oh-my-posh-theme"; do
    rm -rf "$real_dir"
    mkdir -p "$real_dir"
    echo "$SENTINEL_CONTENT" > "$real_dir/sentinel.txt"
done

echo "=== Pre-creating a ~/.gitconfig symlink into the repository ==="
# The repository copy is untracked after #74, so it is absent in a fresh clone and
# the link starts out dangling. Never create it here: the checkout is read-only
# under Docker.
GITCONFIG_RETIRED="$DOTFILES_DIR/.gitconfig"
ln -sfn "$GITCONFIG_RETIRED" "$HOME/.gitconfig"

echo "=== Running install.sh --symlinks-only ==="
bash "$DOTFILES_DIR/install.sh" --symlinks-only

echo "=== Verifying symlinks ==="
EXPECTED_LINKS=(
    "$HOME/.zshrc"
    "$HOME/.bashrc"
    "$HOME/.bash_profile"
    "$HOME/.profile"
    "$HOME/.vimrc"
    "$HOME/.tmux.conf"
)

for file in "${MANIFEST_CLAUDE_FILES[@]}"; do
    EXPECTED_LINKS+=("$HOME/.claude/$file")
done

for link in "${EXPECTED_LINKS[@]}"; do
    if [ -L "$link" ]; then
        echo "  OK: $link"
    else
        echo "  FAIL: $link is not a symlink"
        ERRORS=$((ERRORS + 1))
    fi
done

if [ ! -L "$HOME/.claude/hooks/deny-check.sh" ]; then
    echo "  OK: retired deny-check symlink removed"
else
    echo "  FAIL: retired deny-check symlink still present"
    ERRORS=$((ERRORS + 1))
fi

if [ ! -L "$HOME/.claude/hooks/link-worktree-memory.sh" ]; then
    echo "  OK: retired worktree-memory symlink removed"
else
    echo "  FAIL: retired worktree-memory symlink still present"
    ERRORS=$((ERRORS + 1))
fi

if ! grep -q "link-worktree-memory" "$DOTFILES_DIR/claude/settings.json"; then
    echo "  OK: retired worktree-memory hook is not configured"
else
    echo "  FAIL: retired worktree-memory hook is still configured"
    ERRORS=$((ERRORS + 1))
fi

echo "=== Directory symlinks ==="
for dir_link in "$HOME/.shell-utils" "$HOME/oh-my-posh-theme"; do
    if [ -L "$dir_link" ]; then
        echo "  OK: $dir_link"
    else
        echo "  FAIL: $dir_link is not a symlink"
        ERRORS=$((ERRORS + 1))
    fi
done

echo "=== Verifying the retired .gitconfig symlink was detached from the repository ==="
if [ -L "$HOME/.gitconfig" ]; then
    echo "  FAIL: .gitconfig still points into the repository"
    ERRORS=$((ERRORS + 1))
elif [ -e "$GITCONFIG_RETIRED" ] && ! cmp -s "$HOME/.gitconfig" "$GITCONFIG_RETIRED"; then
    echo "  FAIL: .gitconfig was detached without preserving its contents"
    ERRORS=$((ERRORS + 1))
else
    echo "  OK: .gitconfig no longer points into the repository"
fi

echo "=== Verifying pre-existing directory contents were backed up, not deleted ==="
for rel in .shell-utils oh-my-posh-theme; do
    if grep -rqs "$SENTINEL_CONTENT" "$HOME/.dotfiles-backup"/*/"$rel"/sentinel.txt; then
        echo "  OK: $rel contents preserved under ~/.dotfiles-backup"
    else
        echo "  FAIL: $rel contents were deleted instead of backed up"
        ERRORS=$((ERRORS + 1))
    fi
done

echo "=== Verifying the machine-local .npmrc was preserved ==="
if [ -f "$HOME/.npmrc" ] && [ ! -L "$HOME/.npmrc" ] && grep -q "$NPMRC_CONTENT" "$HOME/.npmrc"; then
    echo "  OK: $HOME/.npmrc remains an unchanged machine-local file"
else
    echo "  FAIL: $HOME/.npmrc was replaced or modified"
    ERRORS=$((ERRORS + 1))
fi

echo "=== Verifying migration from the retired .npmrc symlink ==="
rm "$HOME/.npmrc"
ln -s "$DOTFILES_DIR/.npmrc" "$HOME/.npmrc"
bash "$DOTFILES_DIR/install.sh" --symlinks-only > /dev/null
if [ -f "$HOME/.npmrc" ] && [ ! -L "$HOME/.npmrc" ] \
    && grep -q "Keep authentication tokens out" "$HOME/.npmrc"; then
    echo "  OK: retired symlink migrated to a machine-local file"
else
    echo "  FAIL: retired .npmrc symlink was not migrated"
    ERRORS=$((ERRORS + 1))
fi

echo "=== Verifying a machine-local .gitconfig is not replaced on re-run ==="
GITCONFIG_LOCAL_MARKER="name = machine local identity"
printf '[user]\n\t%s\n' "$GITCONFIG_LOCAL_MARKER" > "$HOME/.gitconfig"
bash "$DOTFILES_DIR/install.sh" --symlinks-only > /dev/null
if [ -f "$HOME/.gitconfig" ] && [ ! -L "$HOME/.gitconfig" ] \
    && grep -q "$GITCONFIG_LOCAL_MARKER" "$HOME/.gitconfig"; then
    echo "  OK: .gitconfig left as an unchanged machine-local file"
else
    echo "  FAIL: .gitconfig was replaced or modified"
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

for file in "${MANIFEST_CLAUDE_FILES[@]}"; do
    link="$HOME/.claude/$file"
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

if [ -f "$HOME/.npmrc" ] && [ ! -L "$HOME/.npmrc" ]; then
    echo "  OK: machine-local .npmrc preserved after uninstall"
else
    echo "  FAIL: machine-local .npmrc was removed by uninstall"
    ERRORS=$((ERRORS + 1))
fi

echo "=== Verifying uninstall left the machine-local .gitconfig alone ==="
if [ -f "$HOME/.gitconfig" ] && [ ! -L "$HOME/.gitconfig" ] \
    && grep -q "$GITCONFIG_LOCAL_MARKER" "$HOME/.gitconfig"; then
    echo "  OK: machine-local .gitconfig preserved after uninstall"
else
    echo "  FAIL: machine-local .gitconfig was removed by uninstall"
    ERRORS=$((ERRORS + 1))
fi

echo "=== Verifying install does not create a .gitconfig where none exists ==="
rm -f "$HOME/.gitconfig"
bash "$DOTFILES_DIR/install.sh" --symlinks-only > /dev/null
if [ ! -e "$HOME/.gitconfig" ] && [ ! -L "$HOME/.gitconfig" ]; then
    echo "  OK: no .gitconfig created on a machine without one"
else
    echo "  FAIL: install created $HOME/.gitconfig"
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
