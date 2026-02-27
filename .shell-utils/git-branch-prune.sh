#!/usr/bin/env zsh
# git-branch-prune: Clean up merged branches (traditional merge and squash merge)

git-branch-prune() {
    PROTECT_BRANCHES='master|develop|trunk|main|staging|production|release'

    if [ -z "$1" ]; then
        :
    else
        PROTECT_BRANCHES="${PROTECT_BRANCHES}|$1"
    fi

    echo "fetching..."
    git fetch --prune

    # メインブランチを特定（origin/プレフィックス付きで取得）
    MAIN_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/@@')
    if [ -z "$MAIN_BRANCH" ]; then
        # HEAD が設定されていない場合は候補から検索（ローカルまたはリモート）
        for branch in trunk main master; do
            if git show-ref --verify --quiet refs/heads/$branch; then
                MAIN_BRANCH=$branch
                break
            elif git show-ref --verify --quiet refs/remotes/origin/$branch; then
                MAIN_BRANCH="origin/$branch"
                break
            fi
        done
    fi

    if [ -z "$MAIN_BRANCH" ]; then
        echo "Error: Could not determine main branch"
        return 1
    fi

    echo "Using main branch: $MAIN_BRANCH"

    # 1. 従来の方法: git branch --merged で検出（メインブランチに対して）
    echo
    echo "=== Checking merged branches (traditional merge) ==="
    MERGED_BRANCHES=""
    git branch --merged "$MAIN_BRANCH" 2>/dev/null | while read branch; do
        branch=$(echo "$branch" | sed 's/^[[:space:]]*\*[[:space:]]*//' | sed 's/^[[:space:]]*//')
        if [ -n "$branch" ]; then
            # 保護ブランチかチェック
            is_protected=0
            for protected in master develop trunk main staging production release; do
                if [ "$branch" = "$protected" ]; then
                    is_protected=1
                    break
                fi
            done
            if [ $is_protected -eq 0 ]; then
                MERGED_BRANCHES="${MERGED_BRANCHES}${branch}"$'\n'
            fi
        fi
    done
    echo "Found $(echo "$MERGED_BRANCHES" | sed '/^$/d' | wc -l | tr -d ' ') branches"

    # 2. GitHub CLI: マージ済みPRからブランチを検出
    echo "=== Checking merged PRs (including squash merge) ==="
    MERGED_PR_BRANCHES=""
    if command -v gh &> /dev/null; then
        gh pr list --state merged --limit 1000 --json headRefName --jq '.[].headRefName' 2>/dev/null | while read branch; do
            if [ -z "$branch" ]; then
                continue
            fi
            # ローカルブランチとして存在するかチェック
            if git show-ref --verify --quiet refs/heads/"$branch"; then
                # 保護ブランチかチェック
                is_protected=0
                for protected in master develop trunk main staging production release; do
                    if [ "$branch" = "$protected" ]; then
                        is_protected=1
                        break
                    fi
                done
                if [ $is_protected -eq 0 ]; then
                    MERGED_PR_BRANCHES="${MERGED_PR_BRANCHES}${branch}"$'\n'
                fi
            fi
        done
        echo "Found $(echo "$MERGED_PR_BRANCHES" | sed '/^$/d' | wc -l | tr -d ' ') branches from merged PRs"
    else
        echo "Warning: gh command not found. Squash-merged branches may not be detected."
    fi

    # 3. 両方の結果を統合（重複排除）
    DELETE_BRANCHES=$(echo -e "${MERGED_BRANCHES}\n${MERGED_PR_BRANCHES}" | sort -u | sed '/^$/d')

    # 4. 現在進行中のブランチ（remained branches）を取得
    REMAINED_BRANCHES=""
    ALL_BRANCHES=$(git branch 2>/dev/null | sed 's/^[[:space:]]*\*[[:space:]]*//' | sed 's/^[[:space:]]*//')
    for branch in ${(f)ALL_BRANCHES}; do
        if [ -z "$branch" ]; then
            continue
        fi
        # 保護ブランチかチェック
        is_protected=0
        for protected in master develop trunk main staging production release; do
            if [ "$branch" = "$protected" ]; then
                is_protected=1
                break
            fi
        done
        # 削除対象かチェック
        is_to_delete=0
        for del_branch in ${(f)DELETE_BRANCHES}; do
            if [ "$branch" = "$del_branch" ]; then
                is_to_delete=1
                break
            fi
        done
        if [ $is_protected -eq 0 ] && [ $is_to_delete -eq 0 ]; then
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
    git branch 2>/dev/null | while read branch; do
        branch=$(echo "$branch" | sed 's/^[[:space:]]*\*[[:space:]]*//' | sed 's/^[[:space:]]*//')
        for protected in master develop trunk main staging production release; do
            if [ "$branch" = "$protected" ]; then
                current_marker=""
                git branch | command grep "^\* $branch" > /dev/null 2>&1 && current_marker="* "
                echo "${current_marker}${branch}"
                break
            fi
        done
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

            # PR検出ブランチかチェック（スカッシュマージ対応）
            is_pr_branch=0
            for pr_branch in ${(f)MERGED_PR_BRANCHES}; do
                if [ "$branch" = "$pr_branch" ]; then
                    is_pr_branch=1
                    break
                fi
            done

            if [ $is_pr_branch -eq 1 ]; then
                # GitHub PR経由で検出されたブランチは強制削除（スカッシュマージ済み）
                if git branch -D "$branch" 2>/dev/null; then
                    echo "✓ Deleted (force): $branch"
                else
                    echo "✗ Failed to delete: $branch"
                    echo "  Reason: $(git branch -D "$branch" 2>&1)"
                    FAILED_BRANCHES+=("$branch")
                fi
            else
                # 通常マージ検出のブランチは安全な削除
                if git branch -d "$branch" 2>/dev/null; then
                    echo "✓ Deleted: $branch"
                else
                    echo "✗ Failed to delete: $branch"
                    echo "  Reason: $(git branch -d "$branch" 2>&1)"
                    FAILED_BRANCHES+=("$branch")
                fi
            fi
        done

        if [ ${#FAILED_BRANCHES[@]} -gt 0 ]; then
            echo
            echo "Some branches could not be deleted. You can manually delete them with:"
            for branch in "${FAILED_BRANCHES[@]}"; do
                echo "  git branch -D $branch"
            done
        fi

        echo "Done!"
    else
        echo
        echo "Cancelled."
    fi
}
