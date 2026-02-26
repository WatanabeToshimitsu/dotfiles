# Dotfiles Best Practices Refactoring - Execution Tracker

## Status Overview

| Task | Description | Status | PR |
|------|-------------|--------|-----|
| 0 | Add Docker test infrastructure | Pending | PR 1 |
| 1 | Add MIT LICENSE | Pending | PR 1 |
| 2 | Replace `which` with `command -v` | Pending | PR 2 |
| 3 | Add backup mechanism in install.sh | Pending | PR 3 |
| 4 | Add `.zshrc.local` sourcing | Pending | PR 4 |
| 5 | Extract `git-branch-prune()` to `.shell-utils/` | Pending | PR 4 |
| 6 | Add `.editorconfig` | Pending | PR 1 |
| 7 | Add `.shellcheckrc` | Pending | PR 1 |
| 8 | Add GitHub Actions CI | Pending | PR 5 |
| 9 | Add `uninstall.sh` | Pending | PR 3 |

## PR Structure (5 PRs)

```
PR Dependency Graph:

PR 1 (static files + Docker) ──────────────────────────────────────────┐
  Branch: refactor/static-files                                        │
  Files: LICENSE, .editorconfig, .shellcheckrc,                        │
         test/Dockerfile.ubuntu, test/test-install.sh                  │
                                                                       │
PR 2 (POSIX compliance) ──────┬────────────────────────────────────────┤
  Branch: refactor/posix-compliance                                    │
  Files: install.sh, .zshrc   │                                        │
                               │                                        │
PR 3 (install.sh improve) ◄───┤ (stacked on PR 2)                     │
  Branch: refactor/install-improvements                                │
  Files: install.sh, uninstall.sh                                      │
                               │                                        │
PR 4 (.zshrc cleanup) ◄───────┘ (stacked on PR 2)                     │
  Branch: refactor/zshrc-cleanup                                       │
  Files: .zshrc, .shell-utils/git-branch-prune.sh                     │
                                                                       │
PR 5 (CI) ◄────────────────────────────────────────────────────────────┘
  Branch: refactor/ci (after PRs 1-4 merged)
  Files: .github/workflows/lint.yml
```

## Branching Strategy

```bash
main ──► refactor/static-files     (PR 1, independent)
main ──► refactor/posix-compliance (PR 2, independent)
       └──► refactor/install-improvements (PR 3, stacked on PR 2)
       └──► refactor/zshrc-cleanup        (PR 4, stacked on PR 2)
main ──► refactor/ci               (PR 5, after PRs 1-4 merged)
```

- PR 1 and PR 2: branch from `main`, can be created and merged in parallel
- PR 3 and PR 4: branch from `refactor/posix-compliance` HEAD (stacked)
- PR 5: created after PRs 1-4 are merged into main

## Execution Phases (Agent Team)

### Phase 0: Foundation (2 agents in parallel)

#### Agent A: "static-files" → PR 1

**Task 0: Create Docker test infrastructure**
- `test/Dockerfile.ubuntu`: FROM ubuntu:22.04, non-root testuser, copy dotfiles
- `test/test-install.sh`: bash -n syntax check, run install.sh, verify symlinks
- Commit: `Add Docker test infrastructure for install.sh`

**Task 1: Add MIT LICENSE**
- MIT license, year 2024, author Toshimitsu Watanabe
- Commit: `Add MIT LICENSE`

**Task 6: Add .editorconfig**
- root=true, UTF-8, LF, trim trailing whitespace
- 2-space indent for sh/zsh/json/yaml/toml/md, 4-space for py
- Commit: `Add .editorconfig for consistent formatting`

**Task 7: Add .shellcheckrc**
- disable=SC1090, disable=SC1091, shell=bash
- Commit: `Add .shellcheckrc`

#### Agent B: "which-fix" → PR 2

**Task 2: Replace `which` with `command -v`**
- `install.sh`: 15 occurrences
- `.zshrc`: 1 occurrence (also fix backtick to `$()` form)
- Verify: `grep -rn '\bwhich\b' install.sh .zshrc` → 0 results
- Commit: `Replace which with command -v for POSIX compliance`

### Phase 1: Core Modifications (2 agents in parallel, after Phase 0)

#### Agent C: "install-sh-refactor" → PR 3

**Task 3: Add backup mechanism in install.sh**
- Add `backup_if_real_file()` helper
- Back up to `~/.dotfiles-backup/YYYYMMDD_HHMMSS/`
- Docker test to verify
- Commit: `Add backup mechanism before symlink creation in install.sh`

**Task 9: Add uninstall.sh**
- Remove symlinks pointing to dotfiles dir (safety check via `readlink`)
- Offer restore from `~/.dotfiles-backup/`
- Docker test: install → uninstall → verify
- Commit: `Add uninstall.sh with backup restore support`

#### Agent D: "zshrc-refactor" → PR 4

**Task 4: Add .zshrc.local sourcing**
- Add before oh-my-posh init: `[[ -f ~/.zshrc.local ]] && source ~/.zshrc.local`
- Commit: `Add .zshrc.local sourcing for machine-specific overrides`

**Task 5: Extract git-branch-prune() to .shell-utils/**
- Move function (lines 200-407) to `.shell-utils/git-branch-prune.sh`
- Add sourcing, keep `gb-prune` alias
- Verify: `wc -l .zshrc` → ~307 lines (down from 513)
- Commit: `Extract git-branch-prune() to .shell-utils/git-branch-prune.sh`

### Phase 2: CI (1 agent, after PRs 1-4 merged)

#### Agent E: "ci-setup" → PR 5

**Task 8: Add GitHub Actions CI**
- `.github/workflows/lint.yml`: shellcheck, bash -n, docker test
- Trigger: push to main, pull_request
- Commit: `Add GitHub Actions CI for shellcheck and install testing`

## File Ownership Map

| File | Tasks | Action | PR |
|------|-------|--------|-----|
| `LICENSE` | 1 | Create | PR 1 |
| `.editorconfig` | 6 | Create | PR 1 |
| `.shellcheckrc` | 7 | Create | PR 1 |
| `test/Dockerfile.ubuntu` | 0 | Create | PR 1 |
| `test/test-install.sh` | 0 | Create | PR 1 |
| `install.sh` | 2, 3 | Modify | PR 2, PR 3 |
| `.zshrc` | 2, 4, 5 | Modify | PR 2, PR 4 |
| `uninstall.sh` | 9 | Create | PR 3 |
| `.shell-utils/git-branch-prune.sh` | 5 | Create | PR 4 |
| `.github/workflows/lint.yml` | 8 | Create | PR 5 |

## Verification (End-to-End)

After all PRs merged:

1. `bash -n install.sh && bash -n uninstall.sh` → exit 0
2. `grep -n '\bwhich\b' install.sh .zshrc` → 0 results
3. `shellcheck install.sh uninstall.sh .shell-utils/ghq-rm.sh .shell-utils/git-branch-prune.sh` → clean
4. `source ~/.zshrc && type git-branch-prune` → function exists
5. `type gb-prune` → alias works
6. `wc -l .zshrc` → ~307 lines (down from 513)
7. `ls LICENSE .editorconfig .shellcheckrc test/Dockerfile.ubuntu .github/workflows/lint.yml` → all exist
8. `docker build -f test/Dockerfile.ubuntu -t dotfiles-test . && docker run dotfiles-test bash test/test-install.sh` → pass

## Agent Team Summary

| Phase | Agent | Tasks | Branch | PR | Parallel? |
|-------|-------|-------|--------|-----|-----------|
| 0 | static-files | 0, 1, 6, 7 | refactor/static-files | PR 1 | Yes (with B) |
| 0 | which-fix | 2 | refactor/posix-compliance | PR 2 | Yes (with A) |
| 1 | install-sh-refactor | 3, 9 | refactor/install-improvements | PR 3 | Yes (with D) |
| 1 | zshrc-refactor | 4, 5 | refactor/zshrc-cleanup | PR 4 | Yes (with C) |
| 2 | ci-setup | 8 | refactor/ci | PR 5 | No (final) |

Total: 5 agents, 3 phases, maximum 2 concurrent agents per phase, 5 PRs
