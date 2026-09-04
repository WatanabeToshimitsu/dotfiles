#!/bin/bash
# herdr-nav-picker: fzf pickers for herdr, run inside a popup (issue #32).
#   ws - pick a workspace and focus it   (cmd+shift+w)
#   ag - pick an agent and focus its pane (cmd+shift+a)
# Picker keys: j/k or arrows = move, l/space/enter = attach, h/q/esc = cancel
set -u

HERDR_BIN="${HERDR_BIN_PATH:-herdr}"

list_ws() {
  "$HERDR_BIN" workspace list | python3 -c '
import json, sys
d = json.load(sys.stdin)["result"]
for w in d["workspaces"]:
    mark = "*" if w["focused"] else " "
    print("%s\t%s [%d] %s" % (w["workspace_id"], mark, w["number"], w["label"]))
'
}

list_ag() {
  "$HERDR_BIN" agent list | python3 -c '
import json, sys
d = json.load(sys.stdin)["result"]
for a in d["agents"]:
    mark = "*" if a["focused"] else " "
    title = a.get("terminal_title_stripped") or a["agent"]
    print("%s\t%s %s: %s (%s)" % (a["pane_id"], mark, a["agent"], title, a["agent_status"]))
'
}

mode="${1:-ws}"
case "$mode" in
  ws) items="$(list_ws)" prompt='workspaces> ' ;;
  ag) items="$(list_ag)" prompt='agents> ' ;;
  *)
    echo "usage: $0 [ws|ag]" >&2
    exit 2
    ;;
esac

sel="$(printf '%s\n' "$items" | fzf --disabled --no-info --layout=reverse \
  --prompt="$prompt" --delimiter='\t' --with-nth=2.. \
  --bind 'j:down,k:up,l:accept,space:accept,h:abort,q:abort')" || exit 0
id="${sel%%$'\t'*}"

case "$mode" in
  ws) "$HERDR_BIN" workspace focus "$id" >/dev/null ;;
  ag) "$HERDR_BIN" agent focus "$id" >/dev/null ;;
esac
