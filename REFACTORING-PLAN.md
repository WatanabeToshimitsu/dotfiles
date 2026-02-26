# Dotfiles Best Practices Refactoring - Execution Tracker

## Status Overview

| Task | Description | Status |
|------|-------------|--------|
| 1 | Add MIT LICENSE | Pending |
| 2 | Replace `which` with `command -v` | Pending |
| 3 | Add backup mechanism in install.sh | Pending |
| 4 | Add `.zshrc.local` sourcing | Pending |
| 5 | Extract `git-branch-prune()` to `.shell-utils/` | Pending |
| 6 | Add `.editorconfig` | Pending |
| 7 | Add `.shellcheckrc` | Pending |
| 8 | Add GitHub Actions CI | Pending |
| 9 | Add `uninstall.sh` | Pending |

## Execution Order

```
Task 1: LICENSE           (no deps, low risk)
Task 2: which -> command -v (no deps, mechanical)
Task 3: Backup mechanism   (no deps)
Task 4: .zshrc.local       (no deps)
Task 5: Extract git-branch-prune (no deps, large .zshrc change)
Task 6: .editorconfig      (no deps)
Task 7: .shellcheckrc      (no deps, should come before Task 8)
Task 8: GitHub Actions CI  (depends on Task 7)
Task 9: uninstall.sh       (references backup format from Task 3)
```

## Batch Plan

- **Batch 1**: Task 1, 2, 3
- **Batch 2**: Task 4, 5, 6
- **Batch 3**: Task 7, 8, 9

## Verification (End-to-End)

After all tasks:

1. `bash -n install.sh && bash -n uninstall.sh` -> exit 0
2. `grep -n '\bwhich\b' install.sh` -> 0 results
3. `shellcheck install.sh uninstall.sh .shell-utils/ghq-rm.sh` -> clean
4. `source ~/.zshrc && type git-branch-prune` -> function exists
5. `type gb-prune` -> alias works
6. `wc -l .zshrc` -> ~307 lines (down from 512)
7. `ls LICENSE .editorconfig .shellcheckrc` -> all exist
