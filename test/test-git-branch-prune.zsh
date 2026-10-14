#!/usr/bin/env zsh
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 LC_ALL=C

TEST_DIR="${${(%):-%N}:A:h}"
UTIL="${TEST_DIR:h}/.shell-utils/git-branch-prune.zsh"
TEST_ROOT=$(mktemp -d)
trap 'rm -rf "$TEST_ROOT"' EXIT
failures=0
cases=0
mkdir "$TEST_ROOT/bin"
for tool in git grep; do
    ln -s "$(command -v "$tool")" "$TEST_ROOT/bin/$tool"
done

run_case() {
    local scenario="$1" expected="$2" fixture="$TEST_ROOT/$1"
    local protection="${3-}" fixture_branch="${4:-feature}"
    local fixture_base_oid fixture_feature_oid fixture_merge_oid fixture_advanced_oid reported_head reported_merge
    cases=$((cases + 1))
    local -a object_format=()
    [[ "$scenario" != sha256 ]] || object_format=(--object-format=sha256)
    mkdir -p "$fixture"
    command git -C "$fixture" init -q -b main "${object_format[@]}"
    command git -C "$fixture" config user.name 'Prune fixture'
    command git -C "$fixture" config user.email 'fixture@example.invalid'
    command git -C "$fixture" config commit.gpgsign false
    command git -C "$fixture" config core.hooksPath /dev/null
    print base > "$fixture/base"
    command git -C "$fixture" add base
    command git -C "$fixture" commit -qm base
    fixture_base_oid=$(command git -C "$fixture" rev-parse HEAD)
    command git -C "$fixture" checkout -qb "$fixture_branch"
    print feature > "$fixture/feature"
    command git -C "$fixture" add feature
    command git -C "$fixture" commit -qm feature
    fixture_feature_oid=$(command git -C "$fixture" rev-parse HEAD)
    print advanced > "$fixture/advanced"
    command git -C "$fixture" add advanced
    command git -C "$fixture" commit -qm advanced
    fixture_advanced_oid=$(command git -C "$fixture" rev-parse HEAD)
    command git -C "$fixture" checkout -q main
    command git -C "$fixture" branch -f "$fixture_branch" "$fixture_feature_oid"
    if [[ "$scenario" == ordinary* ]]; then
        command git -C "$fixture" merge -q --ff-only "$fixture_branch"
    else
        command git -C "$fixture" commit -qm divergence --allow-empty
        command git -C "$fixture" merge -q --squash "$fixture_branch" > /dev/null 2>&1
        command git -C "$fixture" commit -qm squash
    fi
    fixture_merge_oid=$(command git -C "$fixture" rev-parse HEAD)
    command git -C "$fixture" update-ref refs/remotes/origin/main "$fixture_merge_oid"
    command git -C "$fixture" symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main
    reported_head="$fixture_feature_oid"
    reported_merge="$fixture_merge_oid"
    case "$scenario" in
        advanced|duplicate-mixed) command git -C "$fixture" branch -f "$fixture_branch" "$fixture_advanced_oid" ;;
        recreated)
            command git -C "$fixture" branch -D "$fixture_branch" > /dev/null
            command git -C "$fixture" branch "$fixture_branch" "$fixture_advanced_oid" ;;
        unreachable) reported_merge="$fixture_advanced_oid" ;;
        missing-merge) reported_merge='' ;;
        missing-head) reported_head='' ;;
        malformed-oid) reported_head=not-a-commit ;;
        unknown-merge) reported_merge=1111111111111111111111111111111111111111 ;;
        ambiguous-base)
            command git -C "$fixture" branch origin/main "$fixture_merge_oid"
            command git -C "$fixture" update-ref refs/remotes/origin/main "$fixture_base_oid" ;;
        fallback-local|fallback-remote)
            command git -C "$fixture" symbolic-ref --delete refs/remotes/origin/HEAD
            [[ "$scenario" != fallback-remote ]] || command git -C "$fixture" branch -m main work ;;
        selected-base-protected)
            command git -C "$fixture" update-ref refs/remotes/origin/feature "$fixture_merge_oid"
            command git -C "$fixture" symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/feature ;;
        *late-branch) command git -C "$fixture" branch -D "$fixture_branch" > /dev/null ;;
        checked-out) command git -C "$fixture" checkout -q "$fixture_branch" ;;
        linked-worktree) command git -C "$fixture" worktree add -q "$TEST_ROOT/linked" "$fixture_branch" ;;
    esac
    (
        cd "$fixture"
        git() {
            if [[ "$1" == fetch ]]; then
                print fetch >> "$fixture/fetches"
                [[ "$scenario" != fetch-failure ]]
                return $?
            fi
            if [[ "$scenario" == *late-branch && "$*" == *--merged* ]]; then
                command git branch "$fixture_branch" "$fixture_feature_oid"
            fi
            if [[ "$1" == branch && ( "${2:-}" == -D || "${2:-}" == -d ) ]]; then
                print -r -- "$*" >> "$fixture/deletions"
                if [[ "$scenario" == *deletion-failure ]]; then
                    print -u2 'fixture deletion refused'
                    return 1
                fi
            fi
            command git "$@"
        }
        gh() {
            [[ "$scenario" != api-failure && "$scenario" != ordinary-api-failure ]] || return 1
            [[ "$scenario" != empty-api ]] || return 0
            [[ "$scenario" != ordinary* || "$scenario" == ordinary-pr-* ]] || return 0
            [[ "$scenario" != ordinary-pr-mismatch ]] || reported_head="$fixture_advanced_oid"
            [[ "$*" == *headRefOid* ]] || return 1
            if [[ "$scenario" == duplicate-later-valid ]]; then
                printf '%s\t%s\t%s\n' "$fixture_branch" "$fixture_advanced_oid" "$fixture_advanced_oid"
            fi
            if [[ "$scenario" == malformed-oid ]]; then
                printf '%s\t%s\t%s\n' "$fixture_branch" "$fixture_feature_oid" "$fixture_merge_oid"
            fi
            printf '%s\t%s\t%s\n' "$fixture_branch" "$reported_head" "$reported_merge"
            if [[ "$scenario" == duplicate-mixed ]]; then
                printf '%s\t%s\t%s\n' "$fixture_branch" "$fixture_advanced_oid" "$fixture_advanced_oid"
            fi
            [[ "$scenario" != partial-api-failure ]] || return 1
        }
        read() {
            if [[ "${1:-}" == -q ]]; then
                case "$scenario" in
                    changed-head|ordinary-changed-head)
                        command git update-ref "refs/heads/$fixture_branch" "$fixture_advanced_oid" ;;
                    changed-base)
                        command git update-ref refs/remotes/origin/main "$fixture_base_oid" ;;
                    cancelled) return 1 ;;
                esac
                return 0
            fi
            builtin read "$@"
        }
        if [[ "$scenario" == *gh-absent ]]; then
            unfunction gh
            PATH="$TEST_ROOT/bin"
        fi
        source "$UTIL"
        if [[ "$scenario" == no-argument ]]; then
            git-branch-prune
        elif [[ "$scenario" == multiple-arguments ]]; then
            git-branch-prune feature another
        else
            git-branch-prune "$protection"
        fi
    ) > "$fixture/output" 2>&1 || :
    local actual=deleted expected_message=''
    case "$scenario" in
        advanced|recreated|duplicate-mixed) expected_message='local HEAD differs from the merged PR' ;;
        unreachable|unknown-merge|ambiguous-base) expected_message='PR merge commit is not verified' ;;
        missing-merge|missing-head|malformed-oid) expected_message='Incomplete PR commit information' ;;
        api-failure|partial-api-failure) expected_message='PR lookup failed' ;;
        empty-api|*late-branch) expected_message='No branches to delete.' ;;
        fetch-failure) expected_message='Fetch failed; no branches will be deleted.' ;;
        changed-head|ordinary-changed-head|changed-base) expected_message='branch or base changed after candidate selection' ;;
        *protected) expected_message='=== Protected branches ===' ;;
        invalid-pattern) expected_message='Invalid protection pattern' ;;
        multiple-arguments) expected_message='Usage:' ;;
        gh-absent) expected_message='gh command not found' ;;
        checked-out|linked-worktree) expected_message="Failed to delete: $fixture_branch" ;;
        *deletion-failure) expected_message='fixture deletion refused' ;;
        cancelled) expected_message='Cancelled.' ;;
    esac
    command git -C "$fixture" show-ref --verify --quiet "refs/heads/$fixture_branch" && actual=kept
    local displayed_candidates displayed_protected
    displayed_candidates=$(sed -n '/^=== Branches to be deleted/,/^=== Protected branches/p' "$fixture/output")
    displayed_protected=$(sed -n '/^=== Protected branches/,/^=== Remained branches/p' "$fixture/output")
    if [[ "$actual" != "$expected" ]]; then
        print -u2 "FAIL: $scenario expected $expected, got $actual"
        cat "$fixture/output" >&2
        failures=$((failures + 1))
    elif [[ -n "$expected_message" ]] && ! grep -Fq "$expected_message" "$fixture/output"; then
        print -u2 "FAIL: $scenario did not report the expected retention reason"
        cat "$fixture/output" >&2
        failures=$((failures + 1))
    elif [[ ( "$scenario" == invalid-pattern || "$scenario" == multiple-arguments ) && -e "$fixture/fetches" ]]; then
        print -u2 "FAIL: $scenario fetched before rejecting invalid input"
        failures=$((failures + 1))
    elif [[ "$expected" == kept && "$scenario" != checked-out && "$scenario" != linked-worktree &&
            "$scenario" != *deletion-failure && -e "$fixture/deletions" ]]; then
        print -u2 "FAIL: $scenario attempted deletion despite missing evidence"
        failures=$((failures + 1))
    elif [[ -e "$fixture/deletions" ]] &&
        [[ $(grep -Fxc -e "branch -d -- $fixture_branch" -e "branch -D -- $fixture_branch" "$fixture/deletions") -ne 1 ]]; then
        print -u2 "FAIL: $scenario repeated deletion"
        failures=$((failures + 1))
    elif [[ "$scenario" == ordinary* && -e "$fixture/deletions" ]] &&
        ! grep -Fxq -- "branch -d -- $fixture_branch" "$fixture/deletions"; then
        print -u2 "FAIL: $scenario used force deletion despite ordinary merge evidence"
        failures=$((failures + 1))
    elif [[ "$scenario" == *protected ]] &&
        { ! grep -Fxq -- "$fixture_branch" <<< "$displayed_protected" || grep -Fxq -- "$fixture_branch" <<< "$displayed_candidates"; }; then
        print -u2 "FAIL: $scenario did not classify protection consistently"
        failures=$((failures + 1))
    elif [[ "$expected" == deleted ]] && ! grep -Fxq -- "$fixture_branch" <<< "$displayed_candidates"; then
        print -u2 "FAIL: $scenario deleted a branch absent from the candidate display"
        failures=$((failures + 1))
    elif [[ "$expected" == deleted ]] && ! grep -Fq "Deleted branch $fixture_branch (was " "$fixture/output"; then
        print -u2 "FAIL: $scenario omitted the native recovery OID"
        failures=$((failures + 1))
    else
        print "PASS: $scenario"
    fi
}

run_case verified-squash deleted
run_case sha256 deleted
run_case duplicate-later-valid deleted
run_case fallback-local deleted
run_case fallback-remote deleted
run_case ordinary-merge deleted
run_case ordinary-api-failure deleted
run_case ordinary-pr-mismatch deleted
run_case ordinary-pr-match deleted
run_case advanced kept
run_case recreated kept
run_case duplicate-mixed kept
run_case unreachable kept
run_case unknown-merge kept
run_case ambiguous-base kept
run_case missing-merge kept
run_case missing-head kept
run_case api-failure kept
run_case partial-api-failure kept
run_case empty-api kept
run_case malformed-oid kept
run_case fetch-failure kept
run_case changed-head kept
run_case ordinary-changed-head kept
run_case changed-base kept
run_case checked-out kept
run_case linked-worktree kept
run_case deletion-failure kept
run_case cancelled kept
run_case extra-protected kept eatur
run_case ordinary-extra-protected kept '^fea(ture|t)$'
run_case default-protected kept '' release
run_case ordinary-default-protected kept '' release
run_case selected-base-protected kept
run_case invalid-pattern kept '['
run_case multiple-arguments kept
run_case ordinary-late-branch kept '^feature$'
run_case late-branch kept '^feature$'
run_case unmatched-pattern deleted '^other$'
run_case no-argument deleted
run_case gh-absent kept
run_case ordinary-gh-absent deleted
run_case ordinary-deletion-failure kept

[[ "$failures" -eq 0 ]] || exit 1
print "git branch prune tests: ok ($cases cases)"
