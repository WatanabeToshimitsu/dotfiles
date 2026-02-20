# dotfiles

Personal dotfiles for macOS, Linux, and WSL2 environments.

## What's Included

| File / Directory | Description |
|---|---|
| `.zshrc` | Zsh configuration (primary shell) with Zinit plugin manager |
| `.bashrc` / `.bash_profile` | Bash configuration |
| `.vimrc` | Vim settings |
| `.tmux.conf` | tmux settings (prefix: `C-j`, vim-style keybindings) |
| `.zprofile` / `.zshenv` / `.profile` | Shell profile and environment files |
| `.shell-utils/` | Utility scripts (e.g. `ghq-rm.sh`) |
| `oh-my-posh-theme/` | oh-my-posh prompt theme configuration |
| `Brewfile` | Homebrew dependencies |
| `install.sh` | Environment setup script for macOS and Linux |

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

## Key Tools

- **Shell**: Zsh with [Zinit](https://github.com/zdharma-continuum/zinit) (lazy-loaded plugins)
- **Prompt**: [oh-my-posh](https://ohmyposh.dev/)
- **Fuzzy finder**: [fzf](https://github.com/junegunn/fzf) + [ripgrep](https://github.com/BurntSushi/ripgrep) + [bat](https://github.com/sharkdp/bat)
- **Node.js**: [Volta](https://volta.sh/)
- **Python**: [pyenv](https://github.com/pyenv/pyenv) (lazy-initialized)
- **Repository management**: [ghq](https://github.com/x-motemen/ghq)
- **Modern CLI**: [lsd](https://github.com/lsd-rs/lsd) (ls), [bat](https://github.com/sharkdp/bat) (cat), [ripgrep](https://github.com/BurntSushi/ripgrep) (grep)

## Notable Aliases

| Alias | Command |
|---|---|
| `gcd` | `cd` into a ghq-managed repository via fzf |
| `gcode` | Open a ghq-managed repository in VS Code via fzf |
| `gb-prune` | Clean up merged branches (supports squash merge via `gh` CLI) |
| `ghq-rm` | Remove a ghq-managed repository interactively |
