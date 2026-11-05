#!/usr/bin/env zsh
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 LC_ALL=C

TEST_DIR="${${(%):-%N}:A:h}"
UTIL="${TEST_DIR:h}/.shell-utils/git-checkout-worktree.zsh"
TEST_ROOT=$(mktemp -d)
TEST_ROOT=${TEST_ROOT:A}
trap 'rm -rf "$TEST_ROOT"' EXIT

fail() {
  print -u2 "FAIL: $*"
  exit 1
}

repo=$TEST_ROOT/repo
git init -q -b main "$repo"
git -C "$repo" -c user.name=fixture -c user.email=fixture@example.invalid commit -q --allow-empty -m base
for branch in held free gone odd; do
  git -C "$repo" branch "$branch"
done
git -C "$repo" worktree add -q "$TEST_ROOT/held" held
git -C "$repo" worktree add -q "$TEST_ROOT/gone" gone
rm "$TEST_ROOT/gone/.git"
odd_path=$TEST_ROOT/$'odd\npath'
git -C "$repo" worktree add -q "$odd_path" odd

# A shell that loaded the old `gco` alias keeps it unless sourcing removes it.
alias gco='git checkout'
source "$UTIL"

# A branch held by another worktree moves the shell there instead of failing.
cd "$repo"

gco held 2> "$TEST_ROOT/held.err"

[[ $PWD == "$TEST_ROOT/held" ]] || fail "held: PWD=$PWD"
grep -qxF "NOTE: Moved to the worktree holding 'held': $TEST_ROOT/held" "$TEST_ROOT/held.err" || fail "held: no move notice"
[[ $(git -C "$repo" branch --show-current) == main ]] || fail "held: main worktree switched"

# A branch no worktree holds is an ordinary checkout in place.
cd "$repo"

gco free 2> /dev/null

[[ $PWD == "$repo" ]] || fail "free: PWD=$PWD"
[[ $(git branch --show-current) == free ]] || fail "free: not checked out"
git checkout -q main

# A worktree path with a newline survives the porcelain listing.
cd "$repo"

gco odd 2> "$TEST_ROOT/odd.err"

[[ $PWD == "$odd_path" ]] || fail "odd: PWD=$PWD"
[[ $(wc -l < "$TEST_ROOT/odd.err") -eq 1 ]] || fail "odd: notice spans lines"

# A holder whose .git is gone leaves git's own refusal in place.
cd "$repo"

if gco gone 2> "$TEST_ROOT/gone.err"; then
  fail "gone: checkout succeeded"
fi

[[ $PWD == "$repo" ]] || fail "gone: PWD=$PWD"
grep -q "already used by worktree" "$TEST_ROOT/gone.err" || fail "gone: git did not refuse"

# A valid holder listed after a stale one still wins.
git -C "$repo" worktree add -q --force "$TEST_ROOT/gone-copy" gone
cd "$repo"

gco gone 2> /dev/null

[[ $PWD == "$TEST_ROOT/gone-copy" ]] || fail "gone-copy: PWD=$PWD"

# A branch the current worktree holds stays put, even when another worktree holds it too.
git -C "$repo" worktree add -q --force "$TEST_ROOT/main-copy" main
mkdir "$TEST_ROOT/main-copy/sub"
cd "$TEST_ROOT/main-copy/sub"

gco main 2> /dev/null

[[ $PWD == "$TEST_ROOT/main-copy/sub" ]] || fail "own: PWD=$PWD"

# Extra arguments go straight to git checkout, even after a held branch.
cd "$repo"

if gco held --quiet 2> "$TEST_ROOT/extra.err"; then
  fail "extra arguments: checkout succeeded"
fi

[[ $PWD == "$repo" ]] || fail "extra arguments: PWD=$PWD"
grep -q "already used by worktree" "$TEST_ROOT/extra.err" || fail "extra arguments: git did not refuse"

# A lone option stays an option even when a branch of that name is held elsewhere.
git -C "$TEST_ROOT/held" update-ref refs/heads/-q HEAD
git -C "$TEST_ROOT/held" symbolic-ref HEAD refs/heads/-q
cd "$repo"

gco -q

[[ $PWD == "$repo" ]] || fail "option: PWD=$PWD"

print "git checkout worktree tests: ok"
