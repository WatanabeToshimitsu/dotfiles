# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a personal dotfiles repository that manages shell configurations, editor settings, and development environment setup. It targets both macOS (primary, via Homebrew) and Linux (apt/yum/dnf) environments, with WSL2 support.

## Repository Structure

- **Shell configs**: `.zshrc` (primary shell), `.bashrc`, `.bash_profile`, `.zprofile`, `.zshenv`, `.profile`
- **Editor configs**: `.vimrc`, `.tmux.conf`
- **Utilities**: `.shell-utils/` contains helper scripts (`ghq-rm.sh`, `zsh-history-substrig-search.zsh`)
- **Package management**: `Brewfile` for Homebrew dependencies
- **Prompt theme**: `oh-my-posh-theme/` contains the oh-my-posh configuration
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
- **Symlink strategy**: `install.sh` uses an explicit file list (not `.*` glob) to avoid linking `.git`, `.claude`, etc.

## Commands

```bash
# Install dotfiles to a new environment (macOS or Linux)
bash install.sh

# Apply dotfile changes (re-symlink)
bash install.sh
```

## Conventions

- Shell utility scripts go in `.shell-utils/` and are added to PATH via `.zshrc`
- Homebrew dependencies are tracked in `Brewfile`
- Environment-specific configs (private PC, work) are kept at the bottom of `.zshrc` under "Depend on Env" section
- Git aliases use short prefixes: `g`=git, `gb`=branch, `gpl`=pull, `gps`=push, `gco`=checkout
- The `git-branch-prune` function handles both traditional merge and squash-merge cleanup via `gh` CLI
- All tool-dependent aliases use `command -v` guards so `.zshrc` loads safely without those tools installed
