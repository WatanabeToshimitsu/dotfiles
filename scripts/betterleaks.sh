#!/usr/bin/env bash
set -euo pipefail

BETTERLEAKS_VERSION=1.9.0

case "$(uname -s)/$(uname -m)" in
  Darwin/arm64) platform=darwin_arm64 sha256=83dd7eaab13d44a1e8e347a17064cdef153a1478db473276d41b38d55613d3f2 ;;
  Darwin/x86_64) platform=darwin_x64 sha256=68dfd83458d9e7f90663daa7a81c7f944083b170dae82e4f5f8d0581ed519ef1 ;;
  Linux/aarch64 | Linux/arm64) platform=linux_arm64 sha256=1d39116e0a58dc94574715e2aa12a2dbd5062f193eee3fec011fef6ba06bd13b ;;
  Linux/x86_64) platform=linux_x64 sha256=f8b185a39ffcece2a1ca82bf3a4e7435cd81963ffd16b7a9128daf75f35f6de7 ;;
  *)
    echo "betterleaks.sh: unsupported platform: $(uname -s)/$(uname -m)" >&2
    exit 1
    ;;
esac

install_dir="${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/betterleaks/${BETTERLEAKS_VERSION}_${platform}"
binary="$install_dir/betterleaks"

install_betterleaks() (
  archive="betterleaks_${BETTERLEAKS_VERSION}_${platform}.tar.gz"
  mkdir -p "$install_dir"
  # Staying inside install_dir keeps the final mv an atomic same-filesystem rename.
  work_dir="$(mktemp -d "$install_dir/.download.XXXXXX")"
  trap 'rm -rf "$work_dir"' EXIT

  curl --fail --location --silent --show-error \
    "https://github.com/betterleaks/betterleaks/releases/download/v${BETTERLEAKS_VERSION}/${archive}" \
    --output "$work_dir/$archive"
  if command -v sha256sum >/dev/null 2>&1; then
    checksum=(sha256sum)
  else
    checksum=(shasum -a 256)
  fi
  # stdout belongs to betterleaks, so checksum output goes to stderr.
  printf '%s  %s\n' "$sha256" "$work_dir/$archive" \
    | "${checksum[@]}" --check --strict - >&2
  tar -xzf "$work_dir/$archive" -C "$work_dir" betterleaks
  mv "$work_dir/betterleaks" "$binary"
)

installed_version() {
  [ -x "$binary" ] && "$binary" version 2>/dev/null
}

if [ "$(installed_version)" != "$BETTERLEAKS_VERSION" ]; then
  install_betterleaks
fi
if [ "$(installed_version)" != "$BETTERLEAKS_VERSION" ]; then
  echo "betterleaks.sh: $binary does not report version $BETTERLEAKS_VERSION" >&2
  exit 1
fi

exec "$binary" "$@"
