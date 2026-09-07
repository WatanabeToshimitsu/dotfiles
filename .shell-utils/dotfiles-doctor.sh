#!/usr/bin/env bash
# dotfiles-doctor: report drift between this repo and the machine.
# --notify: additionally raise a macOS notification when warnings are found.
# --harness-only: check only the Claude/Headroom agent harness.
set -uo pipefail

# -P resolves ~/.shell-utils (a symlink) so the parent is the real repo.
DOTFILES_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
NOTIFY=0
HARNESS_ONLY=0
WARNINGS=0
EXTERNAL_CHECK_TIMEOUT_SECONDS=8

warn() {
  printf '  WARN: %s\n' "$*"
  WARNINGS=$((WARNINGS + 1))
}

info() {
  printf '  %s\n' "$*"
}

section_ok() {
  if [ "$WARNINGS" -eq "$1" ]; then
    printf '  ok\n'
  fi
}

has_command() {
  command -v "$1" > /dev/null 2>&1
}

run_with_timeout() {
  local seconds="$1"
  shift
  python3 - "$seconds" "$@" <<'PY'
import subprocess
import sys
import os
import signal

try:
    process = subprocess.Popen(sys.argv[2:], start_new_session=True)
    result = process.wait(timeout=float(sys.argv[1]))
except subprocess.TimeoutExpired:
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
    raise SystemExit(124)
except FileNotFoundError:
    raise SystemExit(127)
raise SystemExit(result)
PY
}

strip_ansi() {
  LC_ALL=C sed $'s/\033\\[[0-9;]*m//g'
}

semver_from() {
  grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1 || :
}

headroom_deployment_configured() {
  [ -f "$HOME/.headroom/deploy/default/manifest.json" ]
}

run_headroom_status() {
  headroom install status --profile default
}

run_headroom_savings() {
  headroom output-savings
}

# The proxy reports its own feature flags, which is the only view that reflects
# what the running process actually got. `headroom rollout status` resolves the
# policy from the shell it runs in, so on the host it answers about the host.
# /health exposes a fixed whitelist of flags and no credentials.
run_headroom_runtime_flags() {
  python3 -c '
import json
import sys
import urllib.request

url = "http://127.0.0.1:%s/health" % sys.argv[1]
with urllib.request.urlopen(url, timeout=5) as response:
    flags = json.load(response)["config"]["runtime_env"]
for name in ("HEADROOM_OUTPUT_SHAPER", "HEADROOM_OUTPUT_HOLDOUT"):
    value = flags.get(name)
    print("%s=%s" % (name, "" if value is None else value))
' "${HEADROOM_PORT:-8787}"
}

run_claude_mcp_list() {
  run_with_timeout "$EXTERNAL_CHECK_TIMEOUT_SECONDS" claude mcp list
}

run_claude_version() {
  claude --version
}

run_claude_latest_version() {
  run_with_timeout "$EXTERNAL_CHECK_TIMEOUT_SECONDS" \
    npm view @anthropic-ai/claude-code version
}

run_brew_leaves() {
  brew leaves
}

normalize_brew_formulae() {
  sed -E 's|.*/||' | LC_ALL=C sort -u
}

brewfile_formulae() {
  sed -nE 's/^brew "([^"]+)".*/\1/p' "$DOTFILES_DIR/Brewfile" \
    | normalize_brew_formulae
}

check_headroom_shaper() {
  local flags shaper holdout
  if ! flags=$(run_headroom_runtime_flags 2> /dev/null); then
    warn "Headroom runtime flags could not be read; next: run curl -s http://127.0.0.1:${HEADROOM_PORT:-8787}/health"
    return 0
  fi

  shaper=$(printf '%s\n' "$flags" | sed -n 's/^HEADROOM_OUTPUT_SHAPER=//p' | head -n 1)
  holdout=$(printf '%s\n' "$flags" | sed -n 's/^HEADROOM_OUTPUT_HOLDOUT=//p' | head -n 1)

  if [ "$shaper" = "1" ]; then
    info "output shaper flag reached the proxy"
  else
    warn "proxy is answering but its output shaper is off; next: run install.sh --headroom-only"
  fi

  if [ -n "$holdout" ]; then
    info "output holdout: $holdout"
  else
    info "no output holdout, so the reduction above stays ESTIMATED"
  fi
}

check_headroom() {
  echo "== Headroom proxy =="
  local before=$WARNINGS
  local output status healthy savings method requests saved reduction
  local reachable=0

  if ! has_command headroom; then
    warn "Headroom is not installed; next: rerun install.sh"
  elif ! headroom_deployment_configured; then
    warn "Headroom Claude deployment is missing; next: rerun install.sh"
  else
    if output=$(run_headroom_status 2>&1); then
      status=$(printf '%s\n' "$output" | sed -n 's/^Status:[[:space:]]*//p' | head -n 1)
      healthy=$(printf '%s\n' "$output" | sed -n 's/^Healthy:[[:space:]]*//p' | head -n 1)
      if [[ "$status" == *running* && "$healthy" == yes* ]]; then
        info "deployment is running and proxy is reachable"
        reachable=1
      elif [[ "$status" != *running* && "$healthy" == yes* ]]; then
        warn "Persistent Headroom deployment is stopped while a temporary proxy is reachable; next: close headroom wrap sessions, then run install.sh --headroom-only"
        reachable=1
      elif [[ "$status" == *running* ]]; then
        warn "Headroom deployment is running but its proxy is unreachable; next: run headroom doctor"
      else
        warn "Headroom is stopped or its proxy is unreachable; next: run install.sh --headroom-only, then headroom doctor"
      fi
    else
    warn "Headroom status check failed; next: run headroom doctor"
    fi

    if savings=$(run_headroom_savings 2>&1); then
      if [[ "$savings" == *"No shaped requests recorded yet."* ]]; then
        info "output shaper: 0 shaped requests recorded"
      else
        method=$(printf '%s\n' "$savings" | sed -n 's/^[[:space:]]*Method:[[:space:]]*\([A-Z][A-Z]*\).*/\1/p' | head -n 1)
        requests=$(printf '%s\n' "$savings" | sed -n 's/^[[:space:]]*Requests:[[:space:]]*//p' | head -n 1)
        saved=$(printf '%s\n' "$savings" | sed -n 's/^[[:space:]]*Saved:[[:space:]]*//p' | head -n 1)
        reduction=$(printf '%s\n' "$savings" | sed -n 's/^[[:space:]]*Reduction:[[:space:]]*//p' | head -n 1)
        if [ -n "$requests" ]; then
          info "output shaper: ${method:+$method; }$requests; ${saved:-saved amount unavailable}; ${reduction:-reduction unavailable}"
        else
          info "output shaper: data exists; next: run headroom output-savings for details"
        fi
      fi
    else
      warn "Headroom output-savings check failed; next: run headroom output-savings"
    fi

    if [ "$reachable" -eq 1 ]; then
      check_headroom_shaper
    fi
  fi
  section_ok "$before"
}

check_mcp_servers() {
  echo "== Claude MCP servers =="
  local before=$WARNINGS
  local output plain name line status
  local rows=0 connected=0

  if ! has_command claude; then
    warn "Claude Code is not installed; next: rerun install.sh"
  elif output=$(run_claude_mcp_list 2>&1); then
    while IFS= read -r line; do
      plain=$(printf '%s\n' "$line" | strip_ansi)
      [[ "$plain" == *" - "* ]] || continue
      rows=$((rows + 1))
      name=$(printf '%s\n' "$plain" | sed 's/: .* - .*$/ /; s/^[[:space:]]*//; s/[[:space:]]*$//')
      [ -n "$name" ] || name="unknown"
      if [[ "$plain" == *Connected* ]]; then
        connected=$((connected + 1))
      elif [[ "$plain" == *"command not found"* || "$plain" == *ENOENT* || "$plain" == *Invalid* || "$plain" == *invalid* ]]; then
        warn "MCP server '$name' has a configuration error; next: run claude mcp list and inspect its command"
      elif [[ "$plain" == *Failed* || "$plain" == *Disconnected* || "$plain" == *"Not connected"* ]]; then
        info "MCP server '$name' is not connected (possibly temporary); retry with claude mcp list when you need it"
      else
        warn "MCP server '$name' returned an unrecognized status; next: run claude mcp list and inspect its configuration"
      fi
    done <<< "$output"

    if [ "$rows" -eq 0 ]; then
      warn "Claude MCP check returned no server status; next: run claude mcp list"
    elif [ "$rows" -eq "$connected" ]; then
      info "$connected MCP server(s) connected"
    fi
  else
    status=$?
    if [ "$status" -eq 124 ]; then
      info "MCP status check timed out after ${EXTERNAL_CHECK_TIMEOUT_SECONDS}s; skipped as a possibly temporary outage"
    else
      warn "Claude MCP status check failed; next: run claude mcp list"
    fi
  fi
  section_ok "$before"
}

check_claude_version() {
  echo "== Claude Code version =="
  local before=$WARNINGS
  local local_output latest_output local_version latest_version status

  if ! has_command claude; then
    warn "Claude Code is not installed; next: rerun install.sh"
  elif local_output=$(run_claude_version 2>&1); then
    local_version=$(printf '%s\n' "$local_output" | semver_from)
    if [ -z "$local_version" ]; then
      warn "Claude Code version could not be parsed; next: run claude --version"
    elif ! has_command npm; then
      warn "npm is unavailable, so the latest Claude Code version cannot be checked; next: rerun install.sh"
    elif latest_output=$(run_claude_latest_version 2>&1); then
      latest_version=$(printf '%s\n' "$latest_output" | semver_from)
      if [ -z "$latest_version" ]; then
        warn "Latest Claude Code version could not be parsed; next: run npm view @anthropic-ai/claude-code version"
      elif [ "$local_version" = "$latest_version" ]; then
        info "installed $local_version; latest stable $latest_version"
      else
        warn "Claude Code installed $local_version; latest stable $latest_version; next: run claude update"
      fi
    else
      status=$?
      if [ "$status" -eq 124 ]; then
        info "Latest Claude Code version check timed out after ${EXTERNAL_CHECK_TIMEOUT_SECONDS}s; skipped"
      else
        warn "Latest Claude Code version check failed; next: run npm view @anthropic-ai/claude-code version"
      fi
    fi
  else
    warn "Claude Code version check failed; next: run claude --version"
  fi
  section_ok "$before"
}

check_agent_harness() {
  check_headroom
  check_mcp_servers
  check_claude_version
}

check_brew_drift() {
  echo "== brew leaves not in Brewfile =="
  local before=$WARNINGS
  local formula

  if has_command brew; then
    while IFS= read -r formula; do
      [ -n "$formula" ] && warn "installed but untracked: $formula"
    done < <(comm -23 \
      <(run_brew_leaves | normalize_brew_formulae) \
      <(brewfile_formulae))
  fi
  section_ok "$before"
}

check_local_drift() {
  echo "== broken symlinks (~/, ~/.config, ~/.claude, VS Code) =="
  local before=$WARNINGS
  local name dir link
  while IFS= read -r link; do
    warn "broken symlink: $link"
  done < <(
    find "$HOME" -maxdepth 1 -name ".*" -type l ! -exec test -e {} \; -print 2> /dev/null
    find "$HOME/.config" "$HOME/.claude" "$HOME/Library/Application Support/Code/User" \
      -maxdepth 3 -type l ! -exec test -e {} \; -print 2> /dev/null
  )
  section_ok "$before"

  check_brew_drift

  echo "== agent skills not restored by install.sh =="
  before=$WARNINGS
  for dir in "$HOME/.agents/skills"/*/; do
    [ -d "$dir" ] || continue
    name=$(basename "$dir")
    grep -q ":${name}\"" "$DOTFILES_DIR/install.sh" ||
      warn "skill not in setup_agent_skills: $name"
  done
  section_ok "$before"

  echo "== dotfiles repo state =="
  before=$WARNINGS
  if git -C "$DOTFILES_DIR" status --porcelain 2> /dev/null | grep -q .; then
    warn "uncommitted changes in $DOTFILES_DIR"
  fi
  if [ -n "$(git -C "$DOTFILES_DIR" log --oneline '@{upstream}..HEAD' 2> /dev/null)" ]; then
    warn "unpushed commits in $DOTFILES_DIR"
  fi
  section_ok "$before"
}

parse_options() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --notify) NOTIFY=1 ;;
      --harness-only) HARNESS_ONLY=1 ;;
      -h | --help)
        echo "usage: dotfiles-doctor.sh [--notify] [--harness-only]"
        return 2
        ;;
      *)
        printf 'unknown option: %s\n' "$1" >&2
        return 2
        ;;
    esac
    shift
  done
}

finish() {
  echo
  if [ "$WARNINGS" -eq 0 ]; then
    echo "doctor: all clear"
    return 0
  fi

  echo "doctor: $WARNINGS warning(s)"
  info "full harness diagnostics: ~/.shell-utils/dotfiles-doctor.sh --harness-only"
  if [ "$NOTIFY" -eq 1 ] && has_command osascript; then
    osascript -e "display notification \"$WARNINGS warning(s) — run dotfiles-doctor.sh --harness-only\" with title \"dotfiles-doctor\"" > /dev/null 2>&1 || :
  fi
  return 1
}

main() {
  parse_options "$@" || return $?
  printf 'dotfiles doctor: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  if [ "$HARNESS_ONLY" -eq 0 ]; then
    check_local_drift
  fi
  check_agent_harness
  finish
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
