# ANTHROPIC_BASE_URL and OPENAI_BASE_URL point at the proxy, so Claude Code and
# Codex both fail while it is stopped, with no hint about why. The proxy is a
# launchd job that starts at login, so this only fires when something actually
# went wrong.
#
# The port is probed directly rather than through the headroom CLI, which would
# add a Python start-up to every new shell.

# Resolved at source time: inside a function %N is the function name, not a path.
_HEADROOM_PROXY_CHECK_ROOT="${${(%):-%N}:A:h:h}"

_headroom_proxy_reachable() {
  local port="$1" descriptor
  # Without the module the state is unknowable; stay quiet rather than nag.
  zmodload zsh/net/tcp 2> /dev/null || return 0
  ztcp 127.0.0.1 "$port" 2> /dev/null || return 1
  descriptor="$REPLY"
  ztcp -c "$descriptor" 2> /dev/null
  return 0
}

headroom_proxy_check() {
  local port="${HEADROOM_PORT:-8787}"
  _headroom_proxy_reachable "$port" && return 0
  print -u2 "headroom proxy is not answering on port $port; Claude Code and Codex are routed through it"
  print -u2 "  start it with: bash $_HEADROOM_PROXY_CHECK_ROOT/install.sh --headroom-only"
}
