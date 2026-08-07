#!/usr/bin/env bash
# Runs inside the setup pane with cwd = the fresh worktree checkout.
# Detection order: repo-local .herdr/setup.sh wins, then uv, then one JS package manager.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

say() { printf '\033[1m[worktree-setup] %s\033[0m\n' "$*"; }

run() {
  say "$*"
  "$@"
}

status=0
if [ -x .herdr/setup.sh ]; then
  run bash .herdr/setup.sh || status=$?
else
  if [ -f uv.lock ]; then
    run uv sync || status=$?
  fi
  if [ -f pnpm-lock.yaml ]; then
    run pnpm install --frozen-lockfile || status=$?
  elif [ -f package-lock.json ]; then
    run npm ci || status=$?
  elif [ -f yarn.lock ]; then
    run yarn install --frozen-lockfile || status=$?
  fi
fi

if [ "$status" -eq 0 ]; then
  printf '\033[1;32m[worktree-setup] done\033[0m\n'
  sleep 2
else
  printf '\033[1;31m[worktree-setup] failed (exit %s) — dropping to a shell\033[0m\n' "$status"
  exec bash -i
fi
