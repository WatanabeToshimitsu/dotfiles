#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SANDBOX=$(mktemp -d)
trap 'rm -rf "$SANDBOX"' EXIT
SANDBOX=$(cd "$SANDBOX" && pwd -P)

export GIT_CONFIG_GLOBAL="$SANDBOX/gitconfig" GIT_CONFIG_NOSYSTEM=1
git config --global user.name test
git config --global user.email test@example.com
git config --global init.defaultBranch main
git config --global commit.gpgsign false

REPO="$SANDBOX/repo"
WT="$SANDBOX/wt"
mkdir -p "$SANDBOX/bin" "$WT"
export PATH="$SANDBOX/bin:$PATH"
printf '#!/bin/sh\nprintf "%%s\\n" "%s" "%s"\n' "$REPO" "$WT/merged" > "$SANDBOX/bin/ghq"
mkdir -p "$SANDBOX/pr-heads"
cat > "$SANDBOX/bin/gh" << SH
#!/bin/sh
branch=\$(printf '%s\\n' "\$@" | sed -n '/^--head\$/{n;p;}')
cat "$SANDBOX/pr-heads/\$branch" 2> /dev/null
exit 0
SH
chmod +x "$SANDBOX/bin/ghq" "$SANDBOX/bin/gh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

git init -q --bare "$SANDBOX/remote.git"
git init -q "$REPO"
echo ".claude/" > "$REPO/.gitignore"
git -C "$REPO" add .gitignore
git -C "$REPO" commit -qm init
git -C "$REPO" remote add origin "$SANDBOX/remote.git"
git -C "$REPO" push -q origin main
git -C "$REPO" remote set-head origin main

worktree() {
  git -C "$REPO" worktree add -q -b "$1" "$WT/$1" main
  echo "$1" > "$WT/$1/$1.txt"
  git -C "$WT/$1" add .
  git -C "$WT/$1" commit -qm "$1"
}

merged_pr() {
  git -C "$WT/$1" rev-parse HEAD > "$SANDBOX/pr-heads/$1"
}

merged_worktree() {
  worktree "$1"
  merged_pr "$1"
  git -C "$REPO" merge -q --no-ff "$1" -m "Merge $1"
  git -C "$REPO" push -q origin main
}

merged_worktree merged
worktree squashed
merged_pr squashed
worktree unmerged
worktree moved
echo 0000000000000000000000000000000000000000 > "$SANDBOX/pr-heads/moved"
git -C "$REPO" worktree add -q -b fresh "$WT/fresh" main
merged_worktree dirty
echo edited > "$WT/dirty/dirty.txt"
merged_worktree untracked
echo draft > "$WT/untracked/draft.md"
merged_worktree locked
git -C "$REPO" worktree lock "$WT/locked"
merged_worktree nested
git init -q "$WT/nested/.claude/worktrees/child"
git -C "$REPO" worktree add -q --detach "$WT/detached" main

echo "=== Dry run lists merged worktrees and removes nothing ==="
output=$(bash "$REPO_DIR/.shell-utils/worktree-gc")
grep -Fqx "remove   $WT/merged [merged]" <<< "$output" || fail "dry run did not list the merged worktree: $output"
[ "$(grep -Fc "$WT/merged " <<< "$output")" -eq 1 ] || fail "a repository listed twice by ghq was scanned twice"
[ -d "$WT/merged" ] || fail "dry run removed a worktree"

echo "=== --apply removes merged worktrees and keeps everything else ==="
output=$(bash "$REPO_DIR/.shell-utils/worktree-gc" --apply)
for name in merged squashed; do
  [ ! -e "$WT/$name" ] || fail "$name was not removed: $output"
  git -C "$REPO" rev-parse -q --verify "refs/heads/$name" > /dev/null || fail "branch $name was deleted"
done
for name in unmerged moved fresh dirty untracked locked nested detached; do
  [ -d "$WT/$name" ] || fail "$name was removed: $output"
done
[ "$(cat "$WT/dirty/dirty.txt")" = edited ] || fail "an uncommitted edit was lost"
grep -Fq "keep     $WT/nested [nested]: contains another checkout" <<< "$output" \
  || fail "a worktree holding another checkout was not reported"

echo "=== Unknown options are rejected ==="
if bash "$REPO_DIR/.shell-utils/worktree-gc" --force > /dev/null 2>&1; then
  fail "an unknown option was accepted"
fi

echo ""
echo "All tests passed!"
