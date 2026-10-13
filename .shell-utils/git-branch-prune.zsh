# git-branch-prune: clean up merged branches (incl. squash merges via gh).
# zsh-only (uses ${(f)...} and read -q); sourced from .zshrc.

git-branch-prune() {
    local base_oid current_head current_base pr_rows pr_name pr_head pr_merge deletion_output
    local -A candidate_heads pr_merges
    local extra_protection="${1-}" pattern_status=0 matching_names base_branch
    local -A protected_branches known_branches
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
    MAIN_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null) || MAIN_BRANCH=""
    if [ -z "$MAIN_BRANCH" ]; then
        # HEAD が設定されていない場合は候補から検索（ローカルまたはリモート）
        for branch in trunk main master; do
            if git show-ref --verify --quiet refs/heads/$branch; then
                MAIN_BRANCH="refs/heads/$branch"
                break
            elif git show-ref --verify --quiet refs/remotes/origin/$branch; then
                MAIN_BRANCH="refs/remotes/origin/$branch"
                break
            fi
        done
    fi

    if [ -z "$MAIN_BRANCH" ]; then
        echo "Error: Could not determine main branch"
        return 1
    fi

    if ! base_oid=$(git rev-parse --verify "${MAIN_BRANCH}^{commit}" 2>/dev/null); then
        echo "Error: Could not resolve main branch; no branches will be deleted."
        return 1
    fi

    ALL_BRANCHES=$(git for-each-ref --format='%(refname:lstrip=2)' refs/heads) || return 1
    for branch in ${(f)ALL_BRANCHES}; do
        known_branches[$branch]=1
    done
    base_branch="${MAIN_BRANCH#refs/remotes/origin/}"
    for branch in master develop trunk main staging production release "${base_branch#refs/heads/}"; do
        protected_branches[$branch]=1
    done
    if [ -n "$extra_protection" ]; then
        matching_names=$(print -r -- "$ALL_BRANCHES" | command grep -E -e "$extra_protection") ||
            [ "$?" -eq 1 ] || return 1
        for branch in ${(f)matching_names}; do
            protected_branches[$branch]=1
        done
    fi

    echo "Using main branch: $MAIN_BRANCH"

    # 1. 従来の方法: git branch --merged で検出（メインブランチに対して）
    echo
    echo "=== Checking merged branches (traditional merge) ==="
    MERGED_BRANCHES=""
    git branch --merged "$base_oid" --format='%(refname:lstrip=2)' 2>/dev/null | while read branch; do
        branch=$(echo "$branch" | sed 's/^[[:space:]]*\*[[:space:]]*//' | sed 's/^[[:space:]]*//')
        if [ -n "$branch" ]; then
            if [ -n "${known_branches[$branch]-}" ] && [ -z "${protected_branches[$branch]-}" ]; then
                current_head=$(git rev-parse --verify "refs/heads/${branch}^{commit}" 2>/dev/null) || continue
                candidate_heads[$branch]="$current_head"
                MERGED_BRANCHES="${MERGED_BRANCHES}${branch}"$'\n'
            fi
        fi
    done
    echo "Found $(echo "$MERGED_BRANCHES" | sed '/^$/d' | wc -l | tr -d ' ') branches"

    # 2. GitHub CLI: マージ済みPRからブランチを検出
    echo "=== Checking merged PRs (including squash merge) ==="
    MERGED_PR_BRANCHES=""
    if command -v gh &> /dev/null; then
        if ! pr_rows=$(gh pr list --state merged --limit 1000 --json headRefName,headRefOid,mergeCommit \
            --jq '.[] | [.headRefName, .headRefOid, (.mergeCommit.oid // "")] | @tsv' 2>/dev/null); then
            echo "Warning: PR lookup failed; keeping branches without ordinary merge evidence."
            pr_rows=""
        fi
        while IFS=$'\t' read -r pr_name pr_head pr_merge; do
            [ -n "$pr_name$pr_head$pr_merge" ] || continue
            if ! git check-ref-format "refs/heads/$pr_name" >/dev/null 2>&1 ||
                [[ "$pr_head" == *[^0-9a-f]* || ( ${#pr_head} -ne 40 && ${#pr_head} -ne 64 ) ||
                   "$pr_merge" == *[^0-9a-f]* || ( ${#pr_merge} -ne 40 && ${#pr_merge} -ne 64 ) ]]; then
                echo "Warning: Incomplete PR commit information; keeping PR-only candidates."
                pr_rows=""
                break
            fi
        done <<< "$pr_rows"
        while IFS=$'\t' read -r branch pr_head pr_merge; do
            [ -n "$branch" ] || continue
            [ -z "${candidate_heads[$branch]-}" ] || continue
            [ -n "${known_branches[$branch]-}" ] && [ -z "${protected_branches[$branch]-}" ] || continue
            if current_head=$(git rev-parse --verify "refs/heads/${branch}^{commit}" 2>/dev/null); then
                if [ "$current_head" != "$pr_head" ]; then
                    echo "Skipping PR evidence for $branch: local HEAD differs from the merged PR."
                    continue
                fi
                if ! git merge-base --is-ancestor "$pr_merge" "$base_oid" 2>/dev/null; then
                    echo "Skipping PR evidence for $branch: PR merge commit is not verified in $MAIN_BRANCH."
                    continue
                fi
                candidate_heads[$branch]="$current_head"
                pr_merges[$branch]="$pr_merge"
                MERGED_PR_BRANCHES="${MERGED_PR_BRANCHES}${branch}"$'\n'
            fi
        done <<< "$pr_rows"
        echo "Found $(echo "$MERGED_PR_BRANCHES" | sed '/^$/d' | wc -l | tr -d ' ') branches from merged PRs"
    else
        echo "Warning: gh command not found. Squash-merged branches may not be detected."
    fi

    # 3. 両方の結果を統合（重複排除）
    DELETE_BRANCHES=$(echo -e "${MERGED_BRANCHES}\n${MERGED_PR_BRANCHES}" | sort -u | sed '/^$/d')

    # 4. 現在進行中のブランチ（remained branches）を取得
    REMAINED_BRANCHES=""
    for branch in ${(f)ALL_BRANCHES}; do
        if [ -z "$branch" ]; then
            continue
        fi
        # 削除対象かチェック
        is_to_delete=0
        for del_branch in ${(f)DELETE_BRANCHES}; do
            if [ "$branch" = "$del_branch" ]; then
                is_to_delete=1
                break
            fi
        done
        if [ -z "${protected_branches[$branch]-}" ] && [ $is_to_delete -eq 0 ]; then
            REMAINED_BRANCHES="${REMAINED_BRANCHES}${branch}"$'\n'
        fi
    done

    # 表示
    echo
    echo "=== Branches to be deleted ($(echo "$DELETE_BRANCHES" | sed '/^$/d' | wc -l | tr -d ' ') total) ==="
    if [ -n "$DELETE_BRANCHES" ]; then
        echo "$DELETE_BRANCHES"
    else
        echo "(none)"
    fi

    echo
    echo "=== Protected branches ==="
    for branch in ${(f)ALL_BRANCHES}; do
        if [ -n "${protected_branches[$branch]-}" ]; then
            current_marker=""
            git branch | command grep "^\* $branch" > /dev/null 2>&1 && current_marker="* "
            echo "${current_marker}${branch}"
        fi
    done

    echo
    echo "=== Remained branches (in progress, $(echo "$REMAINED_BRANCHES" | sed '/^$/d' | wc -l | tr -d ' ') total) ==="
    if [ -n "$REMAINED_BRANCHES" ] && [ "$(echo "$REMAINED_BRANCHES" | sed '/^$/d' | wc -l)" -gt 0 ]; then
        echo "$REMAINED_BRANCHES" | sed '/^$/d'
    else
        echo "(none)"
    fi

    if [ -z "$DELETE_BRANCHES" ]; then
        echo
        echo "No branches to delete."
        return 0
    fi

    echo
    echo "Delete these branches? (y/N): "

    if read -q; then
        echo
        echo "Deleting..."
        FAILED_BRANCHES=()
        for branch in ${(f)DELETE_BRANCHES}; do
            if [ -z "$branch" ]; then
                continue
            fi

            if ! current_head=$(git rev-parse --verify "refs/heads/${branch}^{commit}" 2>/dev/null) ||
                [ "$current_head" != "${candidate_heads[$branch]-}" ] ||
                ! current_base=$(git rev-parse --verify "${MAIN_BRANCH}^{commit}" 2>/dev/null) ||
                [ "$current_base" != "$base_oid" ]; then
                echo "Keeping $branch: branch or base changed after candidate selection."
                FAILED_BRANCHES+=("$branch")
                continue
            fi

            # PR検出ブランチかチェック（スカッシュマージ対応）
            is_pr_branch=0
            for pr_branch in ${(f)MERGED_PR_BRANCHES}; do
                if [ "$branch" = "$pr_branch" ]; then
                    is_pr_branch=1
                    break
                fi
            done

            if [ $is_pr_branch -eq 1 ]; then
                if ! git merge-base --is-ancestor "${pr_merges[$branch]}" "$current_base" 2>/dev/null; then
                    echo "Keeping $branch: PR merge commit is no longer verified in $MAIN_BRANCH."
                    FAILED_BRANCHES+=("$branch")
                    continue
                fi
                # update-ref would bypass Git's checked-out-worktree protection.
                if deletion_output=$(git branch -D -- "$branch" 2>&1); then
                    print -r -- "$deletion_output"
                    echo "✓ Deleted (force): $branch"
                else
                    echo "✗ Failed to delete: $branch"
                    print -r -- "$deletion_output"
                    FAILED_BRANCHES+=("$branch")
                fi
            else
                # 通常マージ検出のブランチは安全な削除
                if ! git merge-base --is-ancestor "$current_head" "$current_base" 2>/dev/null; then
                    echo "Keeping $branch: ordinary merge evidence is no longer valid."
                    FAILED_BRANCHES+=("$branch")
                    continue
                fi
                if deletion_output=$(git branch -d -- "$branch" 2>&1); then
                    print -r -- "$deletion_output"
                    echo "✓ Deleted: $branch"
                else
                    echo "✗ Failed to delete: $branch"
                    print -r -- "$deletion_output"
                    FAILED_BRANCHES+=("$branch")
                fi
            fi
        done

        if [ ${#FAILED_BRANCHES[@]} -gt 0 ]; then
            echo
            echo "Some branches were kept. Review the reported reasons before retrying:"
            for branch in "${FAILED_BRANCHES[@]}"; do
                print -r -- "  $branch"
            done
        fi

        echo "Done!"
    else
        echo
        echo "Cancelled."
    fi
}
