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
HARNESS_WINDOW_DAYS=7

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

strip_ansi() {
  LC_ALL=C sed $'s/\033\\[[0-9;]*m//g'
}

semver_from() {
  grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1 || :
}

stats_value() {
  local key="$1" stats="$2"
  printf '%s\n' "$stats" | sed -n "s/^${key}: //p" | head -n 1
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

run_claude_mcp_list() {
  claude mcp list
}

run_claude_version() {
  claude --version
}

run_claude_latest_version() {
  npm view @anthropic-ai/claude-code version
}

compactor_hook_configured() {
  grep -Fq 'compact-tool-output.py' "$HOME/.claude/settings.json" 2> /dev/null
}

run_compactor_stats() {
  python3 "$DOTFILES_DIR/claude/hooks/compact-tool-output.py" \
    stats --days "$HARNESS_WINDOW_DAYS"
}

check_headroom() {
  echo "== Headroom proxy =="
  local before=$WARNINGS
  local output status healthy savings requests saved reduction

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
      elif [[ "$status" != *running* && "$healthy" == yes* ]]; then
        warn "Persistent Headroom deployment is stopped while a temporary proxy is reachable; next: close headroom wrap sessions, then run install.sh --headroom-only"
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
        requests=$(printf '%s\n' "$savings" | sed -n 's/^[[:space:]]*Requests:[[:space:]]*//p' | head -n 1)
        saved=$(printf '%s\n' "$savings" | sed -n 's/^[[:space:]]*Saved:[[:space:]]*//p' | head -n 1)
        reduction=$(printf '%s\n' "$savings" | sed -n 's/^[[:space:]]*Reduction:[[:space:]]*//p' | head -n 1)
        if [ -n "$requests" ]; then
          info "output shaper: $requests; ${saved:-saved amount unavailable}; ${reduction:-reduction unavailable}"
        else
          info "output shaper: data exists; next: run headroom output-savings for details"
        fi
      fi
    else
      warn "Headroom output-savings check failed; next: run headroom output-savings"
    fi
  fi
  section_ok "$before"
}

check_mcp_servers() {
  echo "== Claude MCP servers =="
  local before=$WARNINGS
  local output plain name line
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
      else
        warn "MCP server '$name' is not connected; next: run claude mcp list and inspect that server"
      fi
    done <<< "$output"

    if [ "$rows" -eq 0 ]; then
      warn "Claude MCP check returned no server status; next: run claude mcp list"
    elif [ "$rows" -eq "$connected" ]; then
      info "$connected MCP server(s) connected"
    fi
  else
    warn "Claude MCP status check failed; next: run claude mcp list"
  fi
  section_ok "$before"
}

check_claude_version() {
  echo "== Claude Code version =="
  local before=$WARNINGS
  local local_output latest_output local_version latest_version

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
      warn "Latest Claude Code version check failed; next: run npm view @anthropic-ai/claude-code version"
    fi
  else
    warn "Claude Code version check failed; next: run claude --version"
  fi
  section_ok "$before"
}

check_tool_output_compaction() {
  echo "== Claude tool-output compaction (last ${HARNESS_WINDOW_DAYS} days) =="
  local before=$WARNINGS
  local stats active last_invoked failures archives saved
  local script="$DOTFILES_DIR/claude/hooks/compact-tool-output.py"

  if [ ! -f "$script" ]; then
    warn "Compaction hook script is missing; next: rerun install.sh"
  elif ! compactor_hook_configured; then
    warn "Compaction hook is not configured in Claude settings; next: rerun install.sh"
  elif ! has_command python3; then
    warn "python3 is unavailable, so compaction health cannot be checked; next: rerun install.sh"
  elif stats=$(run_compactor_stats 2>&1); then
    active=$(stats_value "hook active" "$stats")
    last_invoked=$(stats_value "hook last invoked" "$stats")
    failures=$(stats_value "hook failures" "$stats")
    archives=$(stats_value "archives" "$stats")
    saved=$(stats_value "saved" "$stats")

    if [ "$active" = "yes" ]; then
      info "hook active; last invoked ${last_invoked:-unknown}"
      if [ "$archives" = "0" ]; then
        info "0 compactions is healthy: no supported output crossed the threshold"
      fi
    else
      warn "Compaction hook was not observed in ${HARNESS_WINDOW_DAYS} days; next: use a Read/Grep/Glob/Web/MCP tool, then rerun compact-tool-output.py stats"
    fi

    case "$failures" in
      '' | *[!0-9]*)
        warn "Compaction failure count could not be parsed; next: rerun compact-tool-output.py stats"
        ;;
      0) ;;
      *)
        warn "$failures compaction hook failure(s) in ${HARNESS_WINDOW_DAYS} days; next: inspect Claude hook stderr and run the hook tests"
        ;;
    esac

    if [[ "$archives" =~ ^[0-9]+$ && -n "$saved" ]]; then
      info "${archives} compaction(s), saved $saved"
    else
      warn "Compaction savings could not be parsed; next: rerun compact-tool-output.py stats"
    fi
  else
    warn "Compaction stats failed; next: run python3 ~/.claude/hooks/compact-tool-output.py stats"
  fi
  section_ok "$before"
}

check_agent_harness() {
  check_headroom
  check_mcp_servers
  check_claude_version
  check_tool_output_compaction
}

check_local_drift() {
  echo "== broken symlinks (~/, ~/.config, ~/.claude, VS Code) =="
  local before=$WARNINGS
  local name dir formula link
  while IFS= read -r link; do
    warn "broken symlink: $link"
  done < <(
    find "$HOME" -maxdepth 1 -name ".*" -type l ! -exec test -e {} \; -print 2> /dev/null
    find "$HOME/.config" "$HOME/.claude" "$HOME/Library/Application Support/Code/User" \
      -maxdepth 3 -type l ! -exec test -e {} \; -print 2> /dev/null
  )
  section_ok "$before"

  echo "== brew leaves not in Brewfile =="
  before=$WARNINGS
  if has_command brew; then
    while IFS= read -r formula; do
      [ -n "$formula" ] && warn "installed but untracked: $formula"
    done < <(comm -23 <(brew leaves | sort) \
      <(grep '^brew "' "$DOTFILES_DIR/Brewfile" | perl -pe 's/^brew "([^"]+)".*/$1/; s|.*/||' | sort))
  fi
  section_ok "$before"

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
