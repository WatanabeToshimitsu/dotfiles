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
UNVERIFIED=0
EXTERNAL_CHECK_TIMEOUT_SECONDS=8

warn() {
  printf '  [ABNORMAL] WARN: %s\n' "$*"
  WARNINGS=$((WARNINGS + 1))
}

unverified() {
  printf '  [UNVERIFIED] %s\n' "$1"
  UNVERIFIED=$((UNVERIFIED + 1))
  WARNINGS=$((WARNINGS + ${2:-0}))
}

info() {
  printf '  %s\n' "$*"
}

section_ok() {
  if [ "$WARNINGS" -eq "$1" ] && [ "$UNVERIFIED" -eq "${2:-$UNVERIFIED}" ]; then
    info "[HEALTHY] checked scope passed"
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
  run_with_timeout "$EXTERNAL_CHECK_TIMEOUT_SECONDS" headroom install status --profile default
}

run_headroom_savings() {
  run_with_timeout "$EXTERNAL_CHECK_TIMEOUT_SECONDS" headroom output-savings
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
  run_with_timeout "$EXTERNAL_CHECK_TIMEOUT_SECONDS" claude --version
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

# Claude Code derives this path from the project directory, mapping "/" and "."
# onto "-".
agent_memory_dir() {
  printf '%s/.claude/projects/%s/memory\n' \
    "$HOME" "$(printf '%s' "$DOTFILES_DIR" | tr './' '--')"
}

memory_frontmatter() {
  awk 'NR == 1 && $0 != "---" { exit } NR > 1 && $0 == "---" { exit } NR > 1' "$1"
}

memory_field() {
  memory_frontmatter "$1" | sed -nE "s/^[[:space:]]*$2:[[:space:]]*//p" | head -n 1
}

check_headroom_shaper() {
  local flags shaper holdout
  if ! flags=$(run_headroom_runtime_flags 2> /dev/null); then
    unverified "Headroom runtime flags could not be read; next: run curl -s http://127.0.0.1:${HEADROOM_PORT:-8787}/health" 1
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
  local before=$WARNINGS unknown_before=$UNVERIFIED
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
      if [ -z "$status" ] || [ -z "$healthy" ]; then
        unverified "Headroom returned no deployment status; next: run headroom doctor" 1
      elif [[ "$status" == *running* && "$healthy" == yes* ]]; then
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
      unverified "Headroom status check failed; next: run headroom doctor" 1
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
          if [ -z "$method" ] || [ -z "$saved" ] || [ -z "$reduction" ]; then
            unverified "output-savings fields are incomplete; next: run headroom output-savings"
          fi
          info "output shaper: ${method:+$method; }$requests; ${saved:-saved amount unavailable}; ${reduction:-reduction unavailable}"
        else
          unverified "output shaper: data exists; next: run headroom output-savings for details"
        fi
      fi
    else
      unverified "Headroom output-savings check failed; next: run headroom output-savings" 1
    fi

    if [ "$reachable" -eq 1 ]; then
      check_headroom_shaper
    fi
  fi
  section_ok "$before" "$unknown_before"
}

check_mcp_servers() {
  echo "== Claude MCP servers =="
  local before=$WARNINGS unknown_before=$UNVERIFIED
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
        unverified "MCP server '$name' is not connected (possibly temporary); retry with claude mcp list when you need it"
      else
        unverified "MCP server '$name' returned an unrecognized status; next: run claude mcp list and inspect its configuration" 1
      fi
    done <<< "$output"

    if [ "$rows" -eq 0 ]; then
      unverified "Claude MCP check returned no server status; next: run claude mcp list" 1
    elif [ "$rows" -eq "$connected" ]; then
      info "$connected MCP server(s) connected"
    fi
  else
    status=$?
    if [ "$status" -eq 124 ]; then
      unverified "MCP status check timed out after ${EXTERNAL_CHECK_TIMEOUT_SECONDS}s; next: retry claude mcp list"
    else
      unverified "Claude MCP status check failed; next: run claude mcp list" 1
    fi
  fi
  section_ok "$before" "$unknown_before"
}

check_claude_version() {
  echo "== Claude Code version =="
  local before=$WARNINGS unknown_before=$UNVERIFIED
  local local_output latest_output local_version latest_version status

  if ! has_command claude; then
    warn "Claude Code is not installed; next: rerun install.sh"
  elif local_output=$(run_claude_version 2>&1); then
    local_version=$(printf '%s\n' "$local_output" | semver_from)
    if [ -z "$local_version" ]; then
      unverified "Claude Code version could not be parsed; next: run claude --version" 1
    elif ! has_command npm; then
      unverified "npm is unavailable, so the latest Claude Code version cannot be checked; next: rerun install.sh" 1
    elif latest_output=$(run_claude_latest_version 2>&1); then
      latest_version=$(printf '%s\n' "$latest_output" | semver_from)
      if [ -z "$latest_version" ]; then
        unverified "Latest Claude Code version could not be parsed; next: run npm view @anthropic-ai/claude-code version" 1
      elif [ "$local_version" = "$latest_version" ]; then
        info "installed $local_version; latest stable $latest_version"
      else
        warn "Claude Code installed $local_version; latest stable $latest_version; next: run claude update"
      fi
    else
      status=$?
      if [ "$status" -eq 124 ]; then
        unverified "Latest Claude Code version check timed out after ${EXTERNAL_CHECK_TIMEOUT_SECONDS}s; next: retry npm view @anthropic-ai/claude-code version"
      else
        unverified "Latest Claude Code version check failed; next: run npm view @anthropic-ai/claude-code version" 1
      fi
    fi
  else
    unverified "Claude Code version check failed; next: run claude --version" 1
  fi
  section_ok "$before" "$unknown_before"
}

check_agent_harness() {
  check_headroom
  check_mcp_servers
  check_claude_version
}

check_output_compaction() {
  echo "== Output compaction: static user registration and script path =="
  unverified "compaction behavior and effective Claude hook invocation are not exercised; next: inspect /hooks in Claude Code"
  info "compression/restoration tests: python3 -m unittest discover -s claude/hooks/tests -p 'test_compact_tool_output.py'"
  if ! has_command python3; then
    unverified "compaction inspection requires Python 3; next: check python3 --version"
    return 0
  fi
  local output state message
  if output=$(run_with_timeout "$EXTERNAL_CHECK_TIMEOUT_SECONDS" python3 -c "$(cat <<'PY'
import json
from pathlib import Path
import stat
import sys

home = Path(sys.argv[1])
command = 'python3 "$HOME/.claude/hooks/compact-tool-output.py"'

def report(state, message):
    print(f"{state}\t{message}")

try:
    settings = json.loads((home / ".claude/settings.json").read_text())
    disabled = settings.get("disableAllHooks", False)
    if not isinstance(disabled, bool):
        raise ValueError
    if disabled:
        report("unused", "user hooks are disabled; effective settings remain unverified")
        raise SystemExit
    groups = settings.get("hooks", {}).get("PostToolUse", [])
    if not isinstance(groups, list):
        raise ValueError
    registered = False
    for group in groups:
        hooks = group["hooks"]
        if not isinstance(hooks, list):
            raise ValueError
        for hook in hooks:
            entry = hook.get("command", "")
            if not isinstance(entry, str):
                raise ValueError
            if "compact-tool-output.py" not in entry:
                continue
            if hook.get("type") != "command" or entry != command:
                report("unknown", "custom compaction registration; next: inspect /hooks in Claude Code")
                raise SystemExit
            if group.get("matcher", "") not in ("", "*", "Read", "Read|Grep|Glob|WebFetch|WebSearch|mcp__.*"):
                report("unknown", "compaction matcher is outside the checked scope; next: inspect /hooks in Claude Code")
                raise SystemExit
            registered = True
    if not registered:
        report("unused", "no user compaction registration")
        raise SystemExit
except FileNotFoundError:
    report("unused", "no user compaction registration")
    raise SystemExit
except OSError:
    report("unknown", "user hook settings could not be read; next: inspect Claude settings.json permissions")
    raise SystemExit
except (AttributeError, KeyError, TypeError, ValueError):
    report("bad", "user hook settings are invalid; next: validate Claude settings.json")
    raise SystemExit

try:
    if not stat.S_ISREG((home / ".claude/hooks/compact-tool-output.py").stat().st_mode):
        report("bad", "registered compaction path is not a file; next: rerun install.sh")
        raise SystemExit
except FileNotFoundError:
    report("bad", "registered compaction script is missing; next: rerun install.sh")
    raise SystemExit
except OSError:
    report("unknown", "registered compaction path could not be checked; next: check hook permissions")
    raise SystemExit
report("good", "user compaction registration and script file (static only)")
PY
  )" "$HOME" 2> /dev/null
  ); then
    while IFS=$'\t' read -r state message; do
      case "$state" in
        good) info "[HEALTHY] $message" ;;
        bad) warn "$message" ;;
        unused) info "[NOT APPLICABLE] $message" ;;
        unknown) unverified "$message" ;;
      esac
    done <<< "$output"
  else
    unverified "compaction inspection could not run; next: check Python and Claude settings.json"
  fi
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
  else
    info "[NOT APPLICABLE] Homebrew is not installed"
    return 0
  fi
  section_ok "$before"
}

check_memory_promotion() {
  echo "== agent feedback not promoted into this repo =="
  local before=$WARNINGS
  local memory_dir file name promoted

  memory_dir=$(agent_memory_dir)
  if [ ! -d "$memory_dir" ]; then
    info "[NOT APPLICABLE] no agent memory directory for this repository"
    return 0
  fi

  for file in "$memory_dir"/*.md; do
    [ -f "$file" ] || continue
    name=$(basename "$file" .md)
    [ "$name" = MEMORY ] && continue
    [ "$(memory_field "$file" type)" = feedback ] || continue

    promoted=$(memory_field "$file" promoted)
    if [ -z "$promoted" ]; then
      warn "feedback not promoted: $name (record metadata.promoted)"
    elif [ "$promoted" != none ] && [ ! -e "$DOTFILES_DIR/$promoted" ]; then
      warn "promotion target is missing: $name -> $promoted"
    fi
  done
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
  check_memory_promotion

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
    if [ "$UNVERIFIED" -eq 0 ]; then
      echo "doctor: all clear within the checked scope"
    else
      echo "doctor: no warnings; $UNVERIFIED check(s) unverified"
    fi
    return 0
  fi

  echo "doctor: $WARNINGS warning(s)"
  [ "$UNVERIFIED" -eq 0 ] || info "$UNVERIFIED check(s) unverified"
  info "full harness diagnostics: ~/.shell-utils/dotfiles-doctor.sh --harness-only"
  if [ "$NOTIFY" -eq 1 ] && has_command osascript; then
    osascript -e "display notification \"$WARNINGS warning(s) — run dotfiles-doctor.sh --harness-only\" with title \"dotfiles-doctor\"" > /dev/null 2>&1 || :
  fi
  return 1
}

check_codex_sync() {
  echo "== Codex configuration sync =="
  if [ ! -f "$HOME/.codex/dotfiles-sync/state.json" ]; then
    info "[NOT APPLICABLE] not installed; setup: bash install.sh --codex-only --dry-run"
    return 0
  fi
  local output candidate python="" found_python=0
  for candidate in python3 python3.13 python3.11; do
    has_command "$candidate" || continue
    found_python=1
    if "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))' > /dev/null 2>&1; then
      python="$candidate"
      break
    fi
  done
  if [ -z "$python" ]; then
    if [ "$found_python" -eq 0 ]; then
      unverified "Codex sync cannot run: Python is not installed; next: install Python 3.11+ and retry dotfiles-doctor.sh" 1
    else
      unverified "Codex sync cannot run: Python 3.11+ is unavailable; next: check python3 --version and install a supported Python" 1
    fi
    return 0
  fi
  if output=$("$python" "$DOTFILES_DIR/scripts/codex-sync/install.py" check --root "$DOTFILES_DIR" 2>&1); then
    info "[HEALTHY] merged snapshot and managed links are current; native settings remain unmanaged"
    [ -z "$output" ] || info "$output"
  else
    warn "Codex sync needs attention: $output"
  fi
}

main() {
  parse_options "$@" || return $?
  printf 'dotfiles doctor: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  info "scope: Headroom deployment/flags/savings; MCP connectivity; Claude versions; Codex managed snapshot; output compaction"
  unverified "roles, skills and other hook behavior are not exercised; next: inspect their repository tests and /hooks"
  if [ "$HARNESS_ONLY" -eq 0 ]; then
    info "additional scope: managed links, Homebrew, memory promotion, restored skills and repository drift"
    check_local_drift
  fi
  check_agent_harness
  check_output_compaction
  check_codex_sync
  finish
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
