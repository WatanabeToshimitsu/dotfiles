#!/usr/bin/env bash
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$TEST_DIR/.." && pwd)"
TEST_ROOT=$(mktemp -d)
trap 'rm -rf "$TEST_ROOT"' EXIT

export HOME="$TEST_ROOT/home"
export PATH="$TEST_ROOT/bin:$PATH"
export DOTFILES_LIBRARY_MODE=1
export TEST_COMMAND_LOG="$TEST_ROOT/commands.log"
mkdir -p "$HOME" "$TEST_ROOT/bin"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

cat > "$TEST_ROOT/bin/git" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'git %s\n' "$*" >> "$TEST_COMMAND_LOG"
if [ "${1:-}" = "init" ]; then
  mkdir -p "${@: -1}/.git"
  exit 0
fi
if [ "${1:-}" = "-C" ]; then
  directory=$2
  operation=$3
  case "$operation" in
    remote) exit 0 ;;
    fetch) printf '%s\n' "${@: -1}" > "$directory/.fake-commit" ;;
    checkout) exit 0 ;;
    rev-parse) cat "$directory/.fake-commit" ;;
  esac
fi
EOF
chmod +x "$TEST_ROOT/bin/git"

cat > "$TEST_ROOT/bin/npx" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'npx %s\n' "$*" >> "$TEST_COMMAND_LOG"
skill=""
while [ "$#" -gt 0 ]; do
  if [ "$1" = "-s" ]; then
    skill=$2
    break
  fi
  shift
done
[ -n "$skill" ] || exit 1
mkdir -p "$HOME/.claude/skills/$skill"
printf 'fixture\n' > "$HOME/.claude/skills/$skill/SKILL.md"
EOF
chmod +x "$TEST_ROOT/bin/npx"

# shellcheck source=../install.sh
source "$REPO_DIR/install.sh"

setup_agent_skills

[ -f "$HOME/.agents/.dotfiles-dependencies.lock.json" ] \
  || fail "installed dependency state was not recorded"
cmp -s \
  "$REPO_DIR/claude/dependencies.lock.json" \
  "$HOME/.agents/.dotfiles-dependencies.lock.json" \
  || fail "installed dependency state differs from the repository lock"

expected_skills=$(jq '[.skills[].names[]] | length' "$REPO_DIR/claude/dependencies.lock.json")
actual_installs=$(grep -c '^npx .* skills@1\.5\.23 add ' "$TEST_COMMAND_LOG")
[ "$actual_installs" -eq "$expected_skills" ] \
  || fail "expected $expected_skills pinned skill installs, got $actual_installs"

before=$(wc -l < "$TEST_COMMAND_LOG")
setup_agent_skills
after=$(wc -l < "$TEST_COMMAND_LOG")
[ "$before" -eq "$after" ] || fail "unchanged lock reinstalled agent skills"

printf 'Claude dependency tests: ok\n'
