# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a personal dotfiles repository that manages shell configurations, editor settings, and development environment setup. It targets both macOS (primary, via Homebrew) and Linux (apt/yum/dnf) environments, with WSL2 support.

## Repository Structure

- **Shell configs**: `.zshrc` (primary shell), `.bashrc`, `.bash_profile`, `.zprofile`, `.zshenv`, `.profile`
- **Editor configs**: `.vimrc`, `.tmux.conf`
- **Utilities**: `.shell-utils/` contains helper scripts (`ghq-rm.sh`, `git-branch-prune.zsh`, `dotfiles-doctor.sh`)
- **Package management**: `Brewfile` for Homebrew dependencies
- **Prompt theme**: `oh-my-posh-theme/` contains the oh-my-posh configuration
- **Claude Code config**: `claude/` contains global Claude Code settings, hooks, and rules (file-level symlinks to `~/.claude/`)
- **Setup**: `install.sh` for environment provisioning (macOS and Linux), installs tools and symlinks dotfiles

## Key Design Decisions

- **Zsh plugin manager**: Zinit (zdharma-continuum/zinit) with lazy-loading (`wait"0a"`, `wait"0b"`)
- **Prompt**: oh-my-posh (not Powerlevel10k; `.p10k.zsh` has been removed)
- **Node.js version manager**: Volta (not nvm in zsh; nvm is only in `.bashrc`)
- **Python version manager**: pyenv with lazy initialization (unfunction pattern to defer `pyenv init`)
- **Fuzzy finder**: fzf integrated with ripgrep (`rg`) for file search, bat for preview
- **Directory navigation**: enhancd plugin + cd-gitroot + ghq for repository management
- **Modern CLI replacements**: `lsd` (ls), `bat` (cat), `rg` (grep) — all guarded with `command -v` checks
- **SSH**: 1Password SSH agent (`SSH_AUTH_SOCK` points to 1Password agent socket, guarded with socket existence check)
- **Claude Code config**: Stored in `claude/` (not `.claude/`) to avoid project-level config conflict. File-level symlinks to `~/.claude/`
- **Symlink strategy**: `install.sh` uses an explicit file list (not `.*` glob) to avoid linking `.git`, `.claude`, etc.

## Commands

```bash
# Install dotfiles to a new environment (macOS or Linux)
bash install.sh

# Apply dotfile changes (re-symlink)
bash install.sh --symlinks-only
```

## Conventions

- Shell utility scripts go in `.shell-utils/` and are added to PATH via `.zshrc`
- Homebrew dependencies are tracked in `Brewfile`
- Environment-specific configs (private PC, work) are kept at the bottom of `.zshrc` under "Depend on Env" section
- Git aliases use short prefixes: `g`=git, `gb`=branch, `gpl`=pull, `gps`=push, `gco`=checkout
- The `git-branch-prune` function handles both traditional merge and squash-merge cleanup via `gh` CLI
- All tool-dependent aliases use `command -v` guards so `.zshrc` loads safely without those tools installed
- PR and issue bodies are written in Japanese, because they are read for review. Commit messages, titles, code, and comments stay in English

## Parallel Agents

More than one agent (Claude Code and Codex/GPT) works these issues at the same
time. Before starting an issue, confirm nobody else is on it, then claim it.

The `agent:*` labels only help once the other agent cooperates, so check the
observable traces first:

```bash
gh issue view <N> --json state,labels,assignees,comments
gh pr list --state all --search "<N>"
git fetch --prune && git branch -r --list "*<N>*"
git log --oneline origin/main -15
```

If any of those show work already in progress, stop and ask rather than starting
a second implementation.

Claim the issue before touching any file:

```bash
gh issue edit <N> --add-label "agent:claude"   # or agent:codex
```

Leave a comment naming the agent, the branch, and the date. Remove the label with
`--remove-label` if the work is abandoned; a merged PR closes the issue, so the
label can stay in that case.
