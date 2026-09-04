#!/usr/bin/env bash
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$TEST_DIR/.." && pwd)"
SCRIPT="$REPO_DIR/.shell-utils/dotfiles-secrets.sh"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEST_ROOT"' EXIT

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  local expected="$1" file="$2"
  grep -Fq -- "$expected" "$file" || fail "missing output: $expected"
}

mkdir -p "$TEST_ROOT/fake-bin"
cat > "$TEST_ROOT/fake-bin/op" <<'FAKE_OP'
#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "account" ] && [ "${2:-}" = "get" ]; then
  [ "${FAKE_OP_SIGNED_IN:-0}" = "1" ]
  exit
fi

if [ "${1:-}" != "inject" ]; then
  exit 2
fi

if [ "${FAKE_OP_INJECT_FAIL:-0}" = "1" ]; then
  exit 1
fi

output=""
shift
while [ "$#" -gt 0 ]; do
  case "$1" in
    -f) shift ;;
    -i) shift 2 ;;
    -o)
      output="$2"
      shift 2
      ;;
    *) exit 2 ;;
  esac
done

[ -n "$output" ] || exit 2
printf '%s\n' 'export SYNTHETIC_SECRET="rendered"' > "$output"
FAKE_OP
chmod +x "$TEST_ROOT/fake-bin/op"

echo "=== Missing 1Password CLI is rejected ==="
missing_home="$TEST_ROOT/missing-home"
mkdir -p "$missing_home"
if env HOME="$missing_home" PATH="/usr/bin:/bin" "$SCRIPT" \
  > "$TEST_ROOT/missing.out" 2> "$TEST_ROOT/missing.err"; then
  fail "missing op was accepted"
fi
assert_contains "1Password CLI (op) not found" "$TEST_ROOT/missing.err"

echo "=== Signed-out 1Password CLI is rejected ==="
signed_out_home="$TEST_ROOT/signed-out-home"
mkdir -p "$signed_out_home"
if env HOME="$signed_out_home" PATH="$TEST_ROOT/fake-bin:/usr/bin:/bin" \
  FAKE_OP_SIGNED_IN=0 "$SCRIPT" \
  > "$TEST_ROOT/signed-out.out" 2> "$TEST_ROOT/signed-out.err"; then
  fail "signed-out op was accepted"
fi
assert_contains "not signed in to 1Password CLI" "$TEST_ROOT/signed-out.err"
[ ! -e "$signed_out_home/.zshrc.local" ] || fail "signed-out run created a target"

echo "=== Existing target requires --force ==="
existing_home="$TEST_ROOT/existing-home"
mkdir -p "$existing_home"
printf '%s\n' "original" > "$existing_home/.zshrc.local"
if env HOME="$existing_home" PATH="$TEST_ROOT/fake-bin:/usr/bin:/bin" \
  FAKE_OP_SIGNED_IN=1 "$SCRIPT" \
  > "$TEST_ROOT/existing.out" 2> "$TEST_ROOT/existing.err"; then
  fail "existing target was overwritten without --force"
fi
assert_contains "already exists" "$TEST_ROOT/existing.err"
assert_contains "original" "$existing_home/.zshrc.local"

echo "=== Directory target is never replaced ==="
directory_home="$TEST_ROOT/directory-home"
mkdir -p "$directory_home/.zshrc.local"
if env HOME="$directory_home" PATH="$TEST_ROOT/fake-bin:/usr/bin:/bin" \
  FAKE_OP_SIGNED_IN=1 "$SCRIPT" --force \
  > "$TEST_ROOT/directory.out" 2> "$TEST_ROOT/directory.err"; then
  fail "directory target was accepted"
fi
assert_contains "is a directory" "$TEST_ROOT/directory.err"
[ -d "$directory_home/.zshrc.local" ] || fail "directory target was removed"

echo "=== Failed render preserves the existing target ==="
if env HOME="$existing_home" PATH="$TEST_ROOT/fake-bin:/usr/bin:/bin" \
  FAKE_OP_SIGNED_IN=1 FAKE_OP_INJECT_FAIL=1 "$SCRIPT" --force \
  > "$TEST_ROOT/inject-fail.out" 2> "$TEST_ROOT/inject-fail.err"; then
  fail "failed op inject returned success"
fi
assert_contains "failed to render" "$TEST_ROOT/inject-fail.err"
assert_contains "original" "$existing_home/.zshrc.local"

echo "=== Successful render replaces atomically with mode 0600 ==="
env HOME="$existing_home" PATH="$TEST_ROOT/fake-bin:/usr/bin:/bin" \
  FAKE_OP_SIGNED_IN=1 "$SCRIPT" --force \
  > "$TEST_ROOT/success.out" 2> "$TEST_ROOT/success.err"
assert_contains 'SYNTHETIC_SECRET="rendered"' "$existing_home/.zshrc.local"
mode="$(python3 - "$existing_home/.zshrc.local" <<'PY'
import os
import stat
import sys

print(oct(stat.S_IMODE(os.stat(sys.argv[1]).st_mode))[2:])
PY
)"
[ "$mode" = "600" ] \
  || fail "rendered target mode is not 0600"
assert_contains "rendered $existing_home/.zshrc.local" "$TEST_ROOT/success.out"
[ ! -s "$TEST_ROOT/success.err" ] || fail "successful render wrote to stderr"

if find "$existing_home" -name '.zshrc.local.*' -print -quit | grep -q .; then
  fail "temporary secret output was left behind"
fi

echo "dotfiles secret rendering tests: ok"
