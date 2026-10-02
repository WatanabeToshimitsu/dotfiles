#!/usr/bin/env bash
set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CI_FILE="$DOTFILES_DIR/.github/workflows/ci.yml"
INSTALL_FILE="$DOTFILES_DIR/install.sh"
GITLEAKS_FILE="$DOTFILES_DIR/scripts/gitleaks.sh"
SECRET_SCAN_TEST="$DOTFILES_DIR/test/test-secret-scan.sh"

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

grep -Eq '^GITLEAKS_VERSION=[0-9]+\.[0-9]+\.[0-9]+$' "$GITLEAKS_FILE" \
  || fail "Gitleaks version is not pinned"
for platform in darwin_arm64 darwin_x64 linux_arm64 linux_x64; do
  grep -Eq "platform=$platform sha256=[0-9a-f]{64}( |$)" "$GITLEAKS_FILE" \
    || fail "Gitleaks checksum is not pinned for $platform"
done
grep -Fq -- '--check --strict -' "$GITLEAKS_FILE" \
  || fail "Gitleaks checksum is not verified"
! grep -Eq 'GITLEAKS_(VERSION|SHA256)|gitleaks/releases/download' "$CI_FILE" \
  || fail "CI pins Gitleaks outside scripts/gitleaks.sh"
grep -Fq 'scripts/gitleaks.sh git ' "$CI_FILE" \
  || fail "CI history scan does not use scripts/gitleaks.sh"
grep -Fq '/scripts/gitleaks.sh"' "$SECRET_SCAN_TEST" \
  || fail "secret-scan test does not use scripts/gitleaks.sh"
for file in "$CI_FILE" "$SECRET_SCAN_TEST"; do
  ! grep -Eq '(^|[^[:alnum:]_./-])gitleaks[[:space:]]+(git|dir|detect|protect|stdin)([[:space:]]|$)' \
    < <(awk '{ if (sub(/\\$/, "")) printf "%s ", $0; else print }' "$file") \
    || fail "$file runs gitleaks from PATH instead of scripts/gitleaks.sh"
done

echo "External dependency boundary is pinned and verified"
