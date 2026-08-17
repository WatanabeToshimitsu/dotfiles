# dotfiles

[![CI](https://github.com/WatanabeToshimitsu/dotfiles/actions/workflows/ci.yml/badge.svg)](https://github.com/WatanabeToshimitsu/dotfiles/actions/workflows/ci.yml)

Personal dotfiles for macOS, Linux, and WSL2 environments.

## What's Included

| File / Directory                     | Description                                                                      |
| ------------------------------------ | -------------------------------------------------------------------------------- |
| `.zshrc`                             | Zsh configuration (primary shell) with Zinit plugin manager                      |
| `.bashrc` / `.bash_profile`          | Bash configuration (NVM, Volta, Docker)                                          |
| `.vimrc`                             | Vim settings (UTF-8, 2-space tabs, smart search)                                 |
| `.tmux.conf`                         | tmux settings (prefix: `C-j`, vim-style pane/copy keybindings)                   |
| `.zprofile` / `.zshenv` / `.profile` | Shell profile and environment files                                              |
| `.gitconfig`                         | Git configuration                                                                |
| `.huskyrc`                           | Husky git hooks configuration                                                    |
| `.shell-utils/`                      | Utility scripts (`ghq-rm.sh`, `git-branch-prune.zsh`, ...)                       |
| `claude/`                            | [Claude Code](https://claude.ai/code) global settings, hooks, rules, statusline  |
| `.config/`                           | XDG-compliant configs (`git/ignore`, `gh/config.yml`, `ghostty`, `herdr`)        |
| `herdr-plugins/`                     | Self-made [herdr](https://herdr.dev) plugins (loaded via `herdr plugin link`)    |
| `vscode/`                            | VS Code user config (keybindings symlinked, settings bootstrap-copied)           |
| `oh-my-posh-theme/`                  | oh-my-posh prompt theme configuration                                            |
| `Brewfile`                           | Homebrew dependencies (CLI tools, casks, VS Code extensions)                     |
| `install.sh`                         | Environment setup script for macOS and Linux                                     |

## Setup

### macOS / Linux / WSL2

```bash
git clone https://github.com/WatanabeToshimitsu/dotfiles.git ~/dotfiles
cd ~/dotfiles
bash install.sh
```

`install.sh` will:

1. **macOS**: Install Homebrew (if needed), run `brew bundle`, and create symlinks
2. **Linux**: Install packages via apt/yum/dnf (and Homebrew for non-root users), then create symlinks
3. Symlink only specific dotfiles (not `.git`, `.claude`, etc.) to `~/`
4. Symlink VS Code keybindings and bootstrap-copy settings (macOS)
5. Reinstall global agent skills via `npx skills` (see `setup_agent_skills`)
6. Install herdr integrations/plugins and link `herdr-plugins/worktree-setup`

Machine-specific shell config goes in `~/.zshrc.local` (sourced last, never tracked here).

### Secrets

Machine-local secrets also live in `~/.zshrc.local`, generated from
[`templates/zshrc.local.tpl`](templates/zshrc.local.tpl) by running
`dotfiles-secrets.sh` (on `PATH` after `install.sh`). Rendering requires a
signed-in [1Password CLI](https://developer.1password.com/docs/cli/) (`op`);
the resulting file is never tracked by this repo.

## Key Tools

- **Shell**: Zsh with [Zinit](https://github.com/zdharma-continuum/zinit) (lazy-loaded plugins)
- **Prompt**: [oh-my-posh](https://ohmyposh.dev/) (custom theme with OS icon, memory usage, execution time, git status)
- **Fuzzy finder**: [fzf](https://github.com/junegunn/fzf) + [ripgrep](https://github.com/BurntSushi/ripgrep) + [bat](https://github.com/sharkdp/bat)
- **Node.js**: [Volta](https://volta.sh/) (not nvm in zsh)
- **Python**: [pyenv](https://github.com/pyenv/pyenv) (lazy-initialized via unfunction pattern)
- **Repository management**: [ghq](https://github.com/x-motemen/ghq) + fzf integration
- **Modern CLI**: [lsd](https://github.com/lsd-rs/lsd) (ls), [bat](https://github.com/sharkdp/bat) (cat), [ripgrep](https://github.com/BurntSushi/ripgrep) (grep), [zoxide](https://github.com/ajeetdsouza/zoxide) (`z`/`zi` jump)
- **Terminal workspace**: [herdr](https://herdr.dev) on [Ghostty](https://ghostty.org) (agent multiplexer; prefix `cmd+space`)

## Notable Aliases

| Alias      | Command                                                       |
| ---------- | ------------------------------------------------------------- |
| `gcd`      | `cd` into a ghq-managed repository via fzf                    |
| `gcode`    | Open a ghq-managed repository in VS Code via fzf              |
| `gb-prune` | Clean up merged branches (supports squash merge via `gh` CLI) |
| `ghq-rm`   | Remove a ghq-managed repository interactively                 |

## Configuration Storage Strategy

Configuration files are organized by target location:

| Storage Location                         | Target                | Strategy                         |
| ---------------------------------------- | --------------------- | -------------------------------- |
| Root dotfiles (`.zshrc`, `.vimrc`, etc.) | `~/`                  | Direct symlink                   |
| `.config/`                               | `~/.config/`          | XDG Base Directory mirror        |
| `claude/`                                | `~/.claude/`          | Per-CLI directory (non-XDG tool) |
| `vscode/`                                | `~/Library/Application Support/Code/User/` | Symlink (keybindings) / bootstrap copy (settings) |
| `herdr-plugins/`                         | herdr plugin registry | `herdr plugin link` (repo edits apply live) |
| `oh-my-posh-theme/`                      | `~/oh-my-posh-theme/` | Direct directory symlink         |
| `.shell-utils/`                          | `~/.shell-utils/`     | Direct directory symlink         |

**Not tracked by design**: machine-local state (`~/.zshrc.local`, VS Code's live `settings.json` mutations), internal hostnames, and herdr-mirror `hosts.toml` — this repo is public.

**Principle**: Follow XDG Base Directory Specification (`.config/`) by default. For CLI tools that do not respect XDG paths, create a dedicated top-level directory named after the tool (e.g., `claude/` for `~/.claude/`).
