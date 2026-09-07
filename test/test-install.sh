#!/usr/bin/env bash
# Integration test for install.sh
set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ERRORS=0

# shellcheck source=../symlink-manifest.sh
source "$DOTFILES_DIR/symlink-manifest.sh"

# Every link install.sh is expected to create, as "target|source" pairs derived
# from the manifest. Adding a manifest entry extends the assertions below with
# no further edit here.
MANAGED_LINKS=()
for file in "${MANIFEST_FILES[@]}"; do
    MANAGED_LINKS+=("$HOME/$file|$DOTFILES_DIR/$file")
done
for file in "${MANIFEST_CONFIG_FILES[@]}"; do
    MANAGED_LINKS+=("$HOME/$file|$DOTFILES_DIR/$file")
done
for file in "${MANIFEST_CLAUDE_FILES[@]}"; do
    MANAGED_LINKS+=("$HOME/.claude/$file|$DOTFILES_DIR/claude/$file")
done
for dir in "${MANIFEST_DIRS[@]}"; do
    MANAGED_LINKS+=("$HOME/$dir|$DOTFILES_DIR/$dir")
done

echo "=== Syntax check ==="
bash -n "$DOTFILES_DIR/install.sh" || { echo "FAIL: install.sh syntax error"; ERRORS=$((ERRORS + 1)); }
bash -n "$DOTFILES_DIR/uninstall.sh" || { echo "FAIL: uninstall.sh syntax error"; ERRORS=$((ERRORS + 1)); }

echo "=== Pre-creating a machine-local .npmrc ==="
NPMRC_CONTENT="pre-existing npmrc content"
echo "$NPMRC_CONTENT" > "$HOME/.npmrc"

echo "=== Pre-creating retired Claude symlinks ==="
# These point at paths the repository no longer carries, so the links are
# deliberately left dangling; install.sh matches them by readlink target.
for file in "${MANIFEST_CLAUDE_OBSOLETE_FILES[@]}"; do
    mkdir -p "$HOME/.claude/$(dirname "$file")"
    ln -sfn "$DOTFILES_DIR/claude/$file" "$HOME/.claude/$file"
done

echo "=== Pre-creating real directories that install.sh must not delete ==="
SENTINEL_CONTENT="machine-local file that predates the symlink"
for dir in "${MANIFEST_DIRS[@]}"; do
    rm -rf "${HOME:?}/$dir"
    mkdir -p "$HOME/$dir"
    echo "$SENTINEL_CONTENT" > "$HOME/$dir/sentinel.txt"
done

echo "=== Pre-creating the retired ~/.huskyrc symlink ==="
# Husky reads .config/husky/init.sh since #83, so the repository no longer
# carries .huskyrc and the link starts out dangling.
HUSKYRC_RETIRED="$DOTFILES_DIR/.huskyrc"
ln -sfn "$HUSKYRC_RETIRED" "$HOME/.huskyrc"

echo "=== Pre-creating a ~/.gitconfig symlink into the repository ==="
# The repository copy is untracked after #74, so it is absent in a fresh clone and
# the link starts out dangling. Never create it here: the checkout is read-only
# under Docker.
GITCONFIG_RETIRED="$DOTFILES_DIR/.gitconfig"
ln -sfn "$GITCONFIG_RETIRED" "$HOME/.gitconfig"

echo "=== Running install.sh --symlinks-only ==="
bash "$DOTFILES_DIR/install.sh" --symlinks-only

echo "=== Verifying every managed link resolves into the repository ==="
for entry in "${MANAGED_LINKS[@]}"; do
    target="${entry%%|*}"
    source="${entry#*|}"
    rel="${target#"$HOME/"}"
    if [ ! -e "$source" ]; then
        echo "  FAIL: $rel is in the manifest but $source is missing from the repo"
        ERRORS=$((ERRORS + 1))
    elif [ ! -L "$target" ]; then
        echo "  FAIL: $rel is not a symlink"
        ERRORS=$((ERRORS + 1))
    elif [ "$(readlink "$target")" != "$source" ]; then
        echo "  FAIL: $rel points at $(readlink "$target"), expected $source"
        ERRORS=$((ERRORS + 1))
    else
        echo "  OK: $rel"
    fi
done

echo "=== Verifying retired Claude symlinks were removed ==="
for file in "${MANIFEST_CLAUDE_OBSOLETE_FILES[@]}"; do
    if [ ! -L "$HOME/.claude/$file" ]; then
        echo "  OK: retired .claude/$file removed"
    else
        echo "  FAIL: retired .claude/$file still present"
        ERRORS=$((ERRORS + 1))
    fi
done

if ! grep -q "link-worktree-memory" "$DOTFILES_DIR/claude/settings.json"; then
    echo "  OK: retired worktree-memory hook is not configured"
else
    echo "  FAIL: retired worktree-memory hook is still configured"
    ERRORS=$((ERRORS + 1))
fi

echo "=== Verifying the retired .huskyrc symlink was removed ==="
if [ ! -e "$HOME/.huskyrc" ] && [ ! -L "$HOME/.huskyrc" ]; then
    echo "  OK: retired .huskyrc symlink removed"
else
    echo "  FAIL: retired .huskyrc symlink still present"
    ERRORS=$((ERRORS + 1))
fi

echo "=== Verifying the Husky startup file still loads .shell-common ==="
if sh -c '. "$HOME/.config/husky/init.sh"; [ -n "$VOLTA_HOME" ]'; then
    echo "  OK: .config/husky/init.sh loads the shared environment"
else
    echo "  FAIL: .config/husky/init.sh did not load .shell-common"
    ERRORS=$((ERRORS + 1))
fi

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
for rel in "${MANIFEST_DIRS[@]}"; do
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

echo "=== Verifying every managed link was removed ==="
for entry in "${MANAGED_LINKS[@]}"; do
    target="${entry%%|*}"
    rel="${target#"$HOME/"}"
    if [ ! -e "$target" ] && [ ! -L "$target" ]; then
        echo "  OK: $rel removed"
    else
        echo "  FAIL: $rel still present"
        ERRORS=$((ERRORS + 1))
    fi
done

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
