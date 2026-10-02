#!/usr/bin/env bash
set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CI_FILE="$DOTFILES_DIR/.github/workflows/ci.yml"
INSTALL_FILE="$DOTFILES_DIR/install.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

while IFS= read -r action; do
  [[ "$action" =~ ^[^[:space:]@]+/[^[:space:]@]+@[0-9a-f]{40}$ ]] \
    || fail "GitHub Action is not pinned to a full commit SHA: $action"
done < <(awk '$1 == "-" && $2 == "uses:" { print $3 }' "$CI_FILE")

grep -Fq 'suzuki-shunsuke/pinact-action@' "$CI_FILE" \
  || fail "pinact validation is missing"
grep -Fq 'npx --yes json5@2.2.3' "$CI_FILE" \
  || fail "CI json5 version is not pinned"
grep -Fq 'GHQ_VERSION=1.10.1' "$INSTALL_FILE" \
  || fail "ghq version is not pinned"
grep -Fq 'GHQ_SHA256=32e380aa8ac76fdd58758cc06174d9ee5db7270bd0cbcc18138b5d36def91b6b' "$INSTALL_FILE" \
  || fail "ghq checksum is not pinned"
grep -Fq 'sha256sum --check --strict -' "$INSTALL_FILE" \
  || fail "ghq checksum is not verified"

echo "External dependency boundary is pinned and verified"
