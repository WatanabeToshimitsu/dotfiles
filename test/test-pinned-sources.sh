#!/usr/bin/env bash
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$TEST_DIR/.." && pwd)"
TEST_ROOT=$(mktemp -d)
trap 'rm -rf "$TEST_ROOT"' EXIT

export GIT_TERMINAL_PROMPT=0
source_index=0
FETCHED_CHECKOUT=""

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

fetch_exact_source() {
  local repository=$1
  local commit=$2
  source_index=$((source_index + 1))
  FETCHED_CHECKOUT="$TEST_ROOT/source-$source_index"

  git init --quiet "$FETCHED_CHECKOUT"
  git -C "$FETCHED_CHECKOUT" remote add origin "$repository"
  git -C "$FETCHED_CHECKOUT" fetch --quiet --depth 1 origin "$commit"
  git -C "$FETCHED_CHECKOUT" checkout --quiet --detach FETCH_HEAD

  local actual_commit
  actual_commit=$(git -C "$FETCHED_CHECKOUT" rev-parse HEAD)
  [ "$actual_commit" = "$commit" ] \
    || fail "commit mismatch for $repository@$commit"
}

while IFS= read -r source_entry; do
  repository=$(printf '%s' "$source_entry" | jq -r '.repository')
  commit=$(printf '%s' "$source_entry" | jq -r '.commit')
  fetch_exact_source "$repository" "$commit"

  while IFS= read -r skill; do
    skill_found=0
    while IFS= read -r skill_file; do
      if [ "$(basename "$(dirname "$skill_file")")" = "$skill" ] \
        || grep -Eq "^name:[[:space:]]*['\"]?${skill}['\"]?[[:space:]]*$" "$skill_file"; then
        skill_found=1
        break
      fi
    done < <(find "$FETCHED_CHECKOUT" -type f -name SKILL.md -print)
    [ "$skill_found" -eq 1 ] || fail "missing pinned skill: $skill"
  done < <(printf '%s' "$source_entry" | jq -r '.names[]')
done < <(jq -c '.skills[]' "$REPO_DIR/claude/dependencies.lock.json")

while IFS= read -r plugin; do
  name=$(printf '%s' "$plugin" | jq -r '.name')
  source_type=$(printf '%s' "$plugin" | jq -r '.source.source')
  commit=$(printf '%s' "$plugin" | jq -r '.source.sha')

  case "$source_type" in
    git-subdir)
      repository=$(printf '%s' "$plugin" | jq -r '.source.url')
      plugin_path=$(printf '%s' "$plugin" | jq -r '.source.path')
      if [[ "$repository" == git@* ]] || [[ "$repository" == ssh://* ]]; then
        printf 'SKIP authenticated plugin source: %s\n' "$name"
        continue
      fi
      fetch_exact_source "$repository" "$commit"
      [ -d "$FETCHED_CHECKOUT/$plugin_path" ] \
        || fail "missing pinned plugin path: $name"
      if [ ! -f "$FETCHED_CHECKOUT/$plugin_path/.claude-plugin/plugin.json" ]; then
        printf '%s' "$plugin" \
          | jq -e '.strict == false and (.lspServers | type == "object" and length > 0)' \
            > /dev/null \
          || fail "missing manifest or inline component definition: $name"
      fi
      ;;
    github)
      repository="https://github.com/$(printf '%s' "$plugin" | jq -r '.source.repo').git"
      fetch_exact_source "$repository" "$commit"
      while IFS= read -r skill_path; do
        skill_path=${skill_path#./}
        [ -f "$FETCHED_CHECKOUT/$skill_path/SKILL.md" ] \
          || fail "missing pinned plugin skill: $name ($skill_path)"
      done < <(printf '%s' "$plugin" | jq -r '.skills[]')
      ;;
    *)
      fail "unsupported pinned plugin source: $name ($source_type)"
      ;;
  esac
done < <(
  jq -c '
    .extraKnownMarketplaces[]
    | select(.source.source == "settings")
    | .source.plugins[]
  ' "$REPO_DIR/claude/settings.json"
)

printf 'Pinned source verification: ok\n'
