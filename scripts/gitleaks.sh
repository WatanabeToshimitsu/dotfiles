#!/usr/bin/env bash
set -euo pipefail

GITLEAKS_VERSION=8.30.1

case "$(uname -s)/$(uname -m)" in
  Darwin/arm64) platform=darwin_arm64 sha256=b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5 ;;
  Darwin/x86_64) platform=darwin_x64 sha256=dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709 ;;
  Linux/aarch64 | Linux/arm64) platform=linux_arm64 sha256=e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080 ;;
  Linux/x86_64) platform=linux_x64 sha256=551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb ;;
  *)
    echo "gitleaks.sh: unsupported platform: $(uname -s)/$(uname -m)" >&2
    exit 1
    ;;
esac

install_dir="${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/gitleaks/${GITLEAKS_VERSION}_${platform}"
binary="$install_dir/gitleaks"

install_gitleaks() (
  archive="gitleaks_${GITLEAKS_VERSION}_${platform}.tar.gz"
  mkdir -p "$install_dir"
  # Staying inside install_dir keeps the final mv an atomic same-filesystem rename.
  work_dir="$(mktemp -d "$install_dir/.download.XXXXXX")"
  trap 'rm -rf "$work_dir"' EXIT

  curl --fail --location --silent --show-error \
    "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/${archive}" \
    --output "$work_dir/$archive"
  if command -v sha256sum >/dev/null 2>&1; then
    checksum=(sha256sum)
  else
    checksum=(shasum -a 256)
  fi
  # stdout belongs to gitleaks, so checksum output goes to stderr.
  printf '%s  %s\n' "$sha256" "$work_dir/$archive" \
    | "${checksum[@]}" --check --strict - >&2
  tar -xzf "$work_dir/$archive" -C "$work_dir" gitleaks
  mv "$work_dir/gitleaks" "$binary"
)

installed_version() {
  [ -x "$binary" ] && "$binary" version 2>/dev/null
}

if [ "$(installed_version)" != "$GITLEAKS_VERSION" ]; then
  install_gitleaks
fi
if [ "$(installed_version)" != "$GITLEAKS_VERSION" ]; then
  echo "gitleaks.sh: $binary does not report version $GITLEAKS_VERSION" >&2
  exit 1
fi

exec "$binary" "$@"
