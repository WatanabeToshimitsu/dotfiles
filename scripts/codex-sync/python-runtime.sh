#!/usr/bin/env bash

codex_sync_python() {
  local candidate found_python=0
  for candidate in python3 python3.13 python3.11; do
    command -v "$candidate" > /dev/null 2>&1 || continue
    found_python=1
    if "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))' > /dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  if [ "$found_python" -eq 0 ]; then
    printf '%s\n' 'Python is not installed; next: install Python 3.11+ and retry' >&2
    return 127
  fi
  printf '%s\n' 'Python 3.11+ is unavailable; next: check python3 --version and install a supported Python' >&2
  return 1
}
