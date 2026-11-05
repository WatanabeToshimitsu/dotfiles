# `git checkout` refuses a branch another worktree holds; `gco <branch>` moves
# the shell into that worktree instead. Anything else is plain `git checkout`.

(( ${+aliases[gco]} )) && unalias gco

gco() {
  local field dir target
  # HEAD rather than a path comparison: `worktree add --force` lets several worktrees hold one branch.
  if (( $# == 1 )) && [[ $1 != -* && $(git symbolic-ref -q HEAD 2> /dev/null) != "refs/heads/$1" ]]; then
    # -z: without it a newline in a worktree path splits the record.
    # shortcut: a branch mid-rebase or mid-bisect elsewhere is listed as detached, so git's own refusal shows instead; read that worktree's rebase state if this comes up.
    for field in ${(0)"$(git worktree list --porcelain -z 2> /dev/null)"}; do
      case $field in
        "worktree "*) dir=${field#worktree } ;;
        "branch refs/heads/$1") [[ -e $dir/.git ]] && target=$dir && break ;;
      esac
    done
  fi
  if [[ -n $target ]]; then
    local note=NOTE:
    # Color only on a terminal, as git does, so redirected output stays plain.
    [[ -t 2 ]] && note=$'\e[1;35mNOTE:\e[0m'
    # stderr, like git checkout's own "Switched to branch" notice; (q+) keeps an odd path on one pasteable line.
    cd "$target" && print -ru2 -- "$note Moved to the worktree holding '$1': ${(q+)target}"
  else
    git checkout "$@"
  fi
}
