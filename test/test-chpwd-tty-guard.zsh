#!/usr/bin/env zsh
set -euo pipefail

TEST_DIR="${${(%):-%N}:A:h}"
ZSHRC="${TEST_DIR:h}/.zshrc"

dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
touch "$dir/marker"

fail() {
  print -u2 "FAIL: $*"
  exit 1
}

# Load only the chpwd definition; sourcing .zshrc needs zinit and the network.
eval "$(grep -E '^chpwd\(\)' "$ZSHRC")"
(( $+functions[chpwd] )) || fail "chpwd not found in .zshrc"

# Agent shells pipe stdout; a listing there floods their output.
piped=$(cd "$dir")
[[ -z "$piped" ]] || fail "chpwd printed to a pipe: $piped"

# A pty slave as stdout gives a terminal on macOS and Linux, with no tty stdin
# needed (CI has none), unlike pty.spawn and script(1).
tty_out=$(python3 -c '
import os, select, subprocess, sys
master, slave = os.openpty()
subprocess.run(["zsh", "-fc", sys.argv[1]], stdout=slave, stdin=subprocess.DEVNULL, check=True)
# Read before closing the slave: macOS drops buffered pty output on close.
# The timeout turns a missing listing into a failure instead of a hang.
ready, _, _ = select.select([master], [], [], 5)
print(os.read(master, 65536).decode() if ready else "")
' "$(functions chpwd); cd $dir")
[[ "$tty_out" == *marker* ]] || fail "chpwd did not list on a terminal: $tty_out"

print "PASS"
