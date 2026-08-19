#!/bin/bash
# herdr-nav-picker: spatial navigation helper for herdr (dotfiles issue #32).
#   left - focus the pane to the left; at the left edge, open the picker
#   open - open the workspace/agent picker in a temporary split pane
#   pick - internal: the fzf UI, runs inside the temporary pane
# Picker keys: j/k or arrows = move, l/space/enter = attach, h/q/esc = cancel
set -u

HERDR_BIN="${HERDR_BIN_PATH:-herdr}"

list_items() {
  "$HERDR_BIN" workspace list | python3 -c '
import json, sys
d = json.load(sys.stdin)["result"]
for w in d["workspaces"]:
    mark = "*" if w["focused"] else " "
    print("ws\t%s\t%s [%d] %s" % (w["workspace_id"], mark, w["number"], w["label"]))
'
  "$HERDR_BIN" agent list | python3 -c '
import json, sys
d = json.load(sys.stdin)["result"]
for a in d["agents"]:
    mark = "*" if a["focused"] else " "
    title = a.get("terminal_title_stripped") or a["agent"]
    print("ag\t%s\t%s   %s: %s (%s)" % (a["pane_id"], mark, a["agent"], title, a["agent_status"]))
'
}

case "${1:-left}" in
  left)
    out="$("$HERDR_BIN" pane focus --direction left --pane "${HERDR_ACTIVE_PANE_ID:-}" 2>/dev/null)" || out=""
    case "$out" in
      *'"changed":true'*) exit 0 ;;
    esac
    exec "$0" open
    ;;
  open)
    pane_id="$("$HERDR_BIN" pane split --current --direction right --ratio 0.7 --focus |
      python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')"
    sleep 0.2
    "$HERDR_BIN" pane run "$pane_id" "$0" pick
    ;;
  pick)
    # shellcheck disable=SC2064  # expand at trap time is fine: env is stable here
    trap '"$HERDR_BIN" pane close "${HERDR_PANE_ID:-}" >/dev/null 2>&1' EXIT
    sel="$(list_items | fzf --disabled --no-info --layout=reverse \
      --prompt='workspaces / agents> ' \
      --delimiter='\t' --with-nth=3.. \
      --bind 'j:down,k:up,l:accept,space:accept,h:abort,q:abort')" || exit 0
    kind="${sel%%$'\t'*}"
    rest="${sel#*$'\t'}"
    id="${rest%%$'\t'*}"
    case "$kind" in
      ws) "$HERDR_BIN" workspace focus "$id" >/dev/null ;;
      ag) "$HERDR_BIN" agent focus "$id" >/dev/null ;;
    esac
    ;;
  *)
    echo "usage: $0 [left|open|pick]" >&2
    exit 2
    ;;
esac
