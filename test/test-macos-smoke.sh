#!/usr/bin/env bash
set -euo pipefail

[ "$(uname -s)" = "Darwin" ] || {
  printf 'macOS smoke skipped: not Darwin\n'
  exit 0
}

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$TEST_DIR/.." && pwd)"
TEST_ROOT=$(mktemp -d)
trap 'rm -rf "$TEST_ROOT"' EXIT

export HOME="$TEST_ROOT/home"
export PATH="$TEST_ROOT/bin:$PATH"
export DOTFILES_LIBRARY_MODE=1
export LAUNCHCTL_LOG="$TEST_ROOT/launchctl.log"
mkdir -p "$HOME/Library/Application Support/Code/User" "$TEST_ROOT/bin"

cat > "$TEST_ROOT/bin/launchctl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$LAUNCHCTL_LOG"
exit 0
EOF
chmod +x "$TEST_ROOT/bin/launchctl"

# shellcheck source=../install.sh
source "$REPO_DIR/install.sh"

setup_vscode
setup_launchd

[ -L "$HOME/Library/Application Support/Code/User/keybindings.json" ]
[ -f "$HOME/Library/Application Support/Code/User/settings.json" ]

plist="$HOME/Library/LaunchAgents/com.kz86n.dotfiles-doctor.plist"
[ -f "$plist" ]
grep -Fq "$HOME/.shell-utils/dotfiles-doctor.sh" "$plist"
grep -Fq 'bootstrap' "$LAUNCHCTL_LOG"

printf 'macOS smoke tests: ok\n'
