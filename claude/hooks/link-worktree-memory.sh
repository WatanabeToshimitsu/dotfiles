#!/usr/bin/env bash
# SessionStart hook: unify worktree auto-memory into the main repo's memory dir.
# Worktree sessions get their own ~/.claude/projects/<slug>/memory namespace,
# which duplicates the main project's memory. This replaces that dir with a
# symlink to the main project's memory so all sessions share one namespace.
set -u

input=$(cat)
cwd=$(printf '%s' "$input" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("cwd",""))' 2>/dev/null) || exit 0
[ -n "$cwd" ] || exit 0

# absolute --git-common-dir means cwd is a linked worktree; main checkout returns ".git"
gitdir=$(git -C "$cwd" rev-parse --git-common-dir 2>/dev/null) || exit 0
case "$gitdir" in
  /*) ;;
  *) exit 0 ;;
esac
main_root=$(dirname "$gitdir")
[ "$main_root" != "$cwd" ] || exit 0

slug() { printf '%s' "$1" | sed 's/[/.]/-/g'; }
proj_root="$HOME/.claude/projects"
wt_mem="$proj_root/$(slug "$cwd")/memory"
main_mem="$proj_root/$(slug "$main_root")/memory"

[ -L "$wt_mem" ] && exit 0
mkdir -p "$main_mem" || exit 0

if [ -d "$wt_mem" ]; then
  # rescue memory files the main namespace doesn't have, then archive the rest
  for f in "$wt_mem"/*.md; do
    [ -e "$f" ] || continue
    b=$(basename "$f")
    [ "$b" = "MEMORY.md" ] && continue
    [ -e "$main_mem/$b" ] || cp "$f" "$main_mem/$b" 2>/dev/null
  done
  archive="$HOME/.claude/worktree-memory-archive/$(slug "$cwd")-$(date +%s)"
  mkdir -p "$(dirname "$archive")" || exit 0
  mv "$wt_mem" "$archive" || exit 0
fi

mkdir -p "$(dirname "$wt_mem")" || exit 0
ln -s "$main_mem" "$wt_mem" 2>/dev/null
exit 0
