#!/usr/bin/env bash
# worktree.created hook (and manual action): open a setup pane in the workspace.
# Exits silently when there is nothing to set up.
set -uo pipefail

# herdr runs plugin commands with a minimal PATH; make jq/uv/pnpm resolvable.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

H="${HERDR_BIN_PATH:-herdr}"
mode="${1:-event}"

ws="${HERDR_WORKSPACE_ID:-}"
cwd=""
if [ "$mode" = event ] && [ -n "${HERDR_PLUGIN_EVENT_JSON:-}" ]; then
  # worktree.created payload shape: .data.workspace.workspace_id,
  # .data.workspace.worktree.checkout_path (older builds: .data.worktree.*)
  ws=$(printf '%s' "$HERDR_PLUGIN_EVENT_JSON" |
    jq -r '.data.workspace.workspace_id // .data.worktree.open_workspace_id // empty' 2>/dev/null)
  cwd=$(printf '%s' "$HERDR_PLUGIN_EVENT_JSON" |
    jq -r '.data.workspace.worktree.checkout_path // .data.worktree.path // empty' 2>/dev/null)
elif [ -n "${HERDR_PLUGIN_CONTEXT_JSON:-}" ]; then
  cwd=$(printf '%s' "$HERDR_PLUGIN_CONTEXT_JSON" |
    jq -r '.focused_pane_cwd // .workspace_cwd // empty' 2>/dev/null)
fi
[ -n "$ws" ] && [ -n "$cwd" ] || exit 0

has_setup() {
  [ -x "$cwd/.herdr/setup.sh" ] || [ -f "$cwd/uv.lock" ] || [ -f "$cwd/pnpm-lock.yaml" ] ||
    [ -f "$cwd/package-lock.json" ] || [ -f "$cwd/yarn.lock" ]
}
has_setup || exit 0

pane=$("$H" pane list --workspace "$ws" 2>/dev/null | jq -r '.result.panes[0].pane_id // empty')
[ -n "$pane" ] || exit 0

"$H" plugin pane open --plugin "${HERDR_PLUGIN_ID:-kz86n.worktree-setup}" --entrypoint setup \
  --placement split --target-pane "$pane" --direction down --cwd "$cwd" --no-focus >/dev/null
