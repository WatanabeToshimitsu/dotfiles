# git-branch-prune: clean up merged branches (incl. squash merges via gh).
# zsh-only (uses associative arrays and read -q); sourced from .zshrc.

git-branch-prune() {
    local base_ref base_oid base_branch branch head marker current_branch=''
    local snapshot names current_head current_base pr_rows pr_head pr_merge
    local extra_protection="${1-}" pattern_status=0 mode proof reason label deletion_output
    local -A heads protected modes pr_merges
    local -a branches delete_branches protected_display remained failed
    if [ "$#" -gt 1 ]; then
        echo "Usage: git-branch-prune [protection-ERE]"
        return 1
    fi
    if [ -n "$extra_protection" ]; then
        command grep -E -e "$extra_protection" /dev/null >/dev/null 2>&1 || pattern_status=$?
        if [ "$pattern_status" -gt 1 ]; then
            echo "Error: Invalid protection pattern; no branches will be deleted."
            return 1
        fi
    fi

    echo "fetching..."
    if ! git fetch --prune; then
        echo "Error: Fetch failed; no branches will be deleted."
        return 1
    fi
    # Short names can resolve to an unrelated local branch with the same name.
    base_ref=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null) || base_ref=''
    if [ -z "$base_ref" ]; then
        for branch in trunk main master; do
            if git show-ref --verify --quiet "refs/heads/$branch"; then
                base_ref="refs/heads/$branch"
                break
            elif git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
                base_ref="refs/remotes/origin/$branch"
                break
            fi
        done
    fi
    if [ -z "$base_ref" ] || ! base_oid=$(git rev-parse --verify "${base_ref}^{commit}" 2>/dev/null); then
        echo "Error: Could not resolve main branch; no branches will be deleted."
        return 1
    fi

    snapshot=$(git for-each-ref --sort=refname --format='%(refname:lstrip=2)%09%(objectname)%09%(HEAD)' refs/heads) || return 1
    while IFS=$'\t' read -r branch head marker; do
        [ -n "$branch" ] || continue
        branches+=("$branch")
        heads[$branch]="$head"
        [ "$marker" != '*' ] || current_branch="$branch"
    done <<< "$snapshot"
    base_branch="${base_ref#refs/remotes/origin/}"
    for branch in master develop trunk main staging production release "${base_branch#refs/heads/}"; do
        protected[$branch]=1
    done
    if [ -n "$extra_protection" ]; then
        names=$(print -rl -- "${branches[@]}" | command grep -E -e "$extra_protection") ||
            [ "$?" -eq 1 ] || return 1
        for branch in ${(f)names}; do
            protected[$branch]=1
        done
    fi
    echo "Using main branch: $base_ref"
    echo
    echo "=== Checking merged branches (traditional merge) ==="
    names=$(git for-each-ref --merged="$base_oid" --format='%(refname:lstrip=2)' refs/heads) || return 1
    for branch in ${(f)names}; do
        [ -n "${heads[$branch]-}" ] && [ -z "${protected[$branch]-}" ] || continue
        modes[$branch]=-d
    done
    echo "Found ${#modes} branches"
    echo "=== Checking merged PRs (including squash merge) ==="
    if command -v gh &> /dev/null; then
        if ! pr_rows=$(gh pr list --state merged --limit 1000 --json headRefName,headRefOid,mergeCommit \
            --jq '.[] | [.headRefName, .headRefOid, (.mergeCommit.oid // "")] | @tsv' 2>/dev/null); then
            echo "Warning: PR lookup failed; keeping branches without ordinary merge evidence."
            pr_rows=''
        fi
        while IFS=$'\t' read -r branch pr_head pr_merge; do
            [ -n "$branch$pr_head$pr_merge" ] || continue
            if ! git check-ref-format "refs/heads/$branch" >/dev/null 2>&1 ||
                [[ "$pr_head" == *[^0-9a-f]* || ( ${#pr_head} -ne 40 && ${#pr_head} -ne 64 ) ||
                   "$pr_merge" == *[^0-9a-f]* || ( ${#pr_merge} -ne 40 && ${#pr_merge} -ne 64 ) ]]; then
                echo "Warning: Incomplete PR commit information; keeping PR-only candidates."
                pr_rows=''
                break
            fi
        done <<< "$pr_rows"
        while IFS=$'\t' read -r branch pr_head pr_merge; do
            [ -n "$branch" ] && [ -n "${heads[$branch]-}" ] || continue
            [ -z "${protected[$branch]-}" ] && [ -z "${modes[$branch]-}" ] || continue
            if [ "${heads[$branch]}" != "$pr_head" ]; then
                echo "Skipping PR evidence for $branch: local HEAD differs from the merged PR."
            elif ! git merge-base --is-ancestor "$pr_merge" "$base_oid" 2>/dev/null; then
                echo "Skipping PR evidence for $branch: PR merge commit is not verified in $base_ref."
            else
                modes[$branch]=-D
                pr_merges[$branch]="$pr_merge"
            fi
        done <<< "$pr_rows"
        echo "Found ${#pr_merges} branches from merged PRs"
    else
        echo "Warning: gh command not found. Squash-merged branches may not be detected."
    fi

    for branch in "${branches[@]}"; do
        if [ -n "${protected[$branch]-}" ]; then
            marker=''
            [ "$branch" != "$current_branch" ] || marker='* '
            protected_display+=("${marker}${branch}")
        elif [ -n "${modes[$branch]-}" ]; then
            delete_branches+=("$branch")
        else
            remained+=("$branch")
        fi
    done
    echo
    echo "=== Branches to be deleted (${#delete_branches} total) ==="
    print -rl -- "${delete_branches[@]:-(none)}"
    echo
    echo "=== Protected branches ==="
    print -rl -- "${protected_display[@]}"
    echo
    echo "=== Remained branches (in progress, ${#remained} total) ==="
    print -rl -- "${remained[@]:-(none)}"
    echo
    if [ ${#delete_branches} -eq 0 ]; then
        echo "No branches to delete."
        return 0
    fi
    echo "Delete these branches? (y/N): "
    if ! read -q; then
        echo
        echo "Cancelled."
        return 0
    fi

    echo
    echo "Deleting..."
    for branch in "${delete_branches[@]}"; do
        if ! current_head=$(git rev-parse --verify "refs/heads/${branch}^{commit}" 2>/dev/null) ||
            [ "$current_head" != "${heads[$branch]}" ] ||
            ! current_base=$(git rev-parse --verify "${base_ref}^{commit}" 2>/dev/null) ||
            [ "$current_base" != "$base_oid" ]; then
            echo "Keeping $branch: branch or base changed after candidate selection."
            failed+=("$branch")
            continue
        fi
        mode="${modes[$branch]}"
        proof="$current_head"
        reason='ordinary merge evidence is no longer valid.'
        label=''
        if [ "$mode" = -D ]; then
            proof="${pr_merges[$branch]}"
            reason="PR merge commit is no longer verified in $base_ref."
            label=' (force)'
        fi
        if ! git merge-base --is-ancestor "$proof" "$current_base" 2>/dev/null; then
            echo "Keeping $branch: $reason"
            failed+=("$branch")
            continue
        fi
        # update-ref would bypass Git's checked-out-worktree protection.
        if deletion_output=$(git branch "$mode" -- "$branch" 2>&1); then
            print -r -- "$deletion_output"
            echo "✓ Deleted${label}: $branch"
        else
            echo "✗ Failed to delete: $branch"
            print -r -- "$deletion_output"
            failed+=("$branch")
        fi
    done
    if [ ${#failed} -gt 0 ]; then
        echo
        echo "Some branches were kept. Review the reported reasons before retrying:"
        for branch in "${failed[@]}"; do
            print -r -- "  $branch"
        done
    fi
    echo "Done!"
}
