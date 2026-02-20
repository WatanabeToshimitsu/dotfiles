# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a personal dotfiles repository that manages shell configurations, editor settings, and development environment setup. It targets both macOS (primary, via Homebrew) and Linux (apt/yum/dnf) environments, with WSL2 support.

## Repository Structure

- **Shell configs**: `.zshrc` (primary shell), `.bashrc`, `.bash_profile`, `.zprofile`, `.zshenv`, `.profile`
- **Editor configs**: `.vimrc`, `.tmux.conf`
- **Utilities**: `.shell-utils/` contains helper scripts (`ghq-rm.sh`, `zsh-history-substrig-search.zsh`)
- **Package management**: `Brewfile` for Homebrew dependencies
- **Setup**: `install.sh` for initial environment provisioning (Linux-focused, installs brew, tools, symlinks dotfiles)
- **Devcontainer**: `devcontainer-template/` has VS Code devcontainer boilerplate for Python projects

## Key Design Decisions

- **Zsh plugin manager**: Zinit (zdharma-continuum/zinit) with lazy-loading (`wait"0a"`, `wait"0b"`)
- **Prompt**: oh-my-posh (not Powerlevel10k; `.p10k.zsh` has been removed)
- **Node.js version manager**: Volta (not nvm in zsh; nvm is only in `.bashrc`)
- **Python version manager**: pyenv with lazy initialization (unfunction pattern to defer `pyenv init`)
- **Fuzzy finder**: fzf integrated with ripgrep (`rg`) for file search, bat for preview
- **Directory navigation**: enhancd plugin + cd-gitroot + ghq for repository management
- **Modern CLI replacements**: `lsd` (ls), `bat` (cat), `rg` (grep)
- **SSH**: 1Password SSH agent (`SSH_AUTH_SOCK` points to 1Password agent socket)
- **Symlink strategy**: `install.sh` uses `ln -fs ~/dotfiles/.* ~/` to link all dotfiles

## Commands

```bash
# Install dotfiles to a new environment (Linux)
bash install.sh

# Install Homebrew packages (macOS)
brew bundle --file=Brewfile

# Apply dotfile changes (re-symlink)
ln -fs ~/dotfiles/.* ~/
```

## Conventions

- Shell utility scripts go in `.shell-utils/` and are added to PATH via `.zshrc`
- Homebrew dependencies are tracked in `Brewfile`
- Environment-specific configs (private PC, work) are kept at the bottom of `.zshrc` under "Depend on Env" section
- Git aliases use short prefixes: `g`=git, `gb`=branch, `gpl`=pull, `gps`=push, `gco`=checkout
- The `git-branch-prune` function handles both traditional merge and squash-merge cleanup via `gh` CLI
