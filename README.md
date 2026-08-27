# dotfiles

[![CI](https://github.com/WatanabeToshimitsu/dotfiles/actions/workflows/ci.yml/badge.svg)](https://github.com/WatanabeToshimitsu/dotfiles/actions/workflows/ci.yml)

Personal dotfiles for macOS, Linux, and WSL2 environments.

## What's Included

| File / Directory                     | Description                                                                      |
| ------------------------------------ | -------------------------------------------------------------------------------- |
| `.zshrc`                             | Zsh configuration (primary shell) with Zinit plugin manager                      |
| `.bashrc` / `.bash_profile`          | Bash configuration (NVM, Volta, Docker)                                          |
| `.vimrc`                             | Vim settings (UTF-8, 2-space tabs, smart search)                                 |
| `.tmux.conf`                         | tmux settings — kept as fallback for remote/ssh hosts without herdr              |
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

To reapply only the managed symlinks without installing packages or tools:

```bash
bash install.sh --symlinks-only
```

### Codespaces

GitHub Settings → Codespaces → enable "Automatically install dotfiles" and select this repo.
`install.sh` then runs automatically on codespace creation.
Machine-specific config still goes in `~/.zshrc.local`.

## Key Tools

- **Shell**: Zsh with [Zinit](https://github.com/zdharma-continuum/zinit) (lazy-loaded plugins)
- **Prompt**: [oh-my-posh](https://ohmyposh.dev/) (custom theme with OS icon, memory usage, execution time, git status)
- **Fuzzy finder**: [fzf](https://github.com/junegunn/fzf) + [ripgrep](https://github.com/BurntSushi/ripgrep) + [bat](https://github.com/sharkdp/bat)
- **Node.js**: [Volta](https://volta.sh/) (not nvm in zsh)
- **Python**: [pyenv](https://github.com/pyenv/pyenv) (lazy-initialized via unfunction pattern)
- **Repository management**: [ghq](https://github.com/x-motemen/ghq) + fzf integration
- **Modern CLI**: [lsd](https://github.com/lsd-rs/lsd) (ls), [bat](https://github.com/sharkdp/bat) (cat), [ripgrep](https://github.com/BurntSushi/ripgrep) (grep), [zoxide](https://github.com/ajeetdsouza/zoxide) (`z`/`zi` jump)
- **Terminal workspace**: [herdr](https://herdr.dev) on [Ghostty](https://ghostty.org) (agent multiplexer; prefix `cmd+space`)
- **Editor**: [Neovim](https://neovim.io) with [LazyVim](https://www.lazyvim.org) (`$EDITOR`; vscodevim keymaps ported, plugins pinned via `lazy-lock.json`)
- **File manager**: [yazi](https://yazi-rs.github.io) (image/video/PDF preview via kitty graphics)

## Terminal File Workflow

View and edit files entirely inside herdr panes — both yazi and Neovim render
images through the kitty graphics protocol (Ghostty and herdr both support it):

- **Browse**: `y` (yazi, shell cwd follows on exit) or `prefix+y` (temporary herdr pane); `Enter` opens `$EDITOR`
- **Edit**: `nvim` = LazyVim; `gvim` picks a ghq repo via fzf and opens it at the repo root
- **Images in the editor**: snacks.image renders PNG inline (JPG/WebP/GIF need imagemagick); `<leader>fy` opens yazi.nvim inside Neovim
- **Fallbacks**: `.vimrc` stays for servers (`vi` = plain vim), VS Code remains installed (`gcode`)

## Notable Aliases

| Alias      | Command                                                       |
| ---------- | ------------------------------------------------------------- |
| `gcd`      | `cd` into a ghq-managed repository via fzf                    |
| `gcode`    | Open a ghq-managed repository in VS Code via fzf              |
| `gvim`     | Open a ghq-managed repository in Neovim via fzf (cwd follows) |
| `y`        | yazi file manager (shell cwd follows on exit)                 |
| `gb-prune` | Clean up merged branches (supports squash merge via `gh` CLI) |
| `ghq-rm`   | Remove a ghq-managed repository interactively                 |

## Claude Tool Output Compaction

Large Read, Grep, Glob, Web, and MCP results are shortened before entering the
conversation. The full result is retained locally for seven days with user-only
permissions and can be queried through the `expand-tool-output` skill.

Show savings from the retained archives when deciding whether the hook is useful:

```bash
python3 ~/.claude/hooks/compact-tool-output.py stats
```

The weekly doctor checks only the last hook invocation and one unresolved error.
It does not aggregate compaction counts or savings. Error records contain the
exception type and time, never tool payloads or exception messages.

## Claude Bash Sandbox Canary

The Claude Code Bash sandbox is available as a macOS-only opt-in trial:

```bash
claude-sandbox --check
claude-sandbox
```

The default `claude` command stays unchanged. The trial blocks common credentials,
does not pre-allow package caches or registries, and keeps only the known `gh` and
Docker compatibility exceptions. See [`claude/SANDBOX.md`](claude/SANDBOX.md) for
the boundary and rollback.

## Claude Auto Memory

Claude Code's repository-scoped auto memory is the only active project-learning
path. It is shared across worktrees without a custom hook. See
[`claude/AUTO-MEMORY.md`](claude/AUTO-MEMORY.md) for the verified behavior and
legacy-data policy.

## Headroom Proxy

`install.sh` installs Headroom 0.36.5 with `uv` and maintains a user-scoped
Claude proxy on port 8787. It uses Docker when available and a native scheduled
task otherwise. The beta output shaper is enabled and Claude Code is routed
through the proxy from new shell sessions.

`dotfiles-doctor.sh` prints the reported measurement method next to the
reduction. `ESTIMATED` compares shaped output against a synthetic baseline
and can report a confidence band wider than the reduction itself, so it is
not a basis for deciding whether the proxy earns its place. `MEASURED`
requires an unshaped control arm via `HEADROOM_OUTPUT_HOLDOUT`.

Learn the preferred response length again after enough Claude history has
accumulated:

```bash
headroom learn --verbosity --apply --all
```

Check the proxy and output-shaping savings:

```bash
headroom install status
headroom doctor
headroom output-savings
```

Run the complete agent-harness diagnostic (Headroom reachability, MCP
connections, Claude Code version drift, and tool-output compaction):

```bash
~/.shell-utils/dotfiles-doctor.sh --harness-only
```

If Docker is unavailable, rerunning `install.sh` migrates an existing Docker
deployment to Headroom's native scheduled recovery instead of leaving a stale
container deployment behind.

```bash
./install.sh --headroom-only
```

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

**Not tracked by design**: machine-local state (`~/.zshrc.local`, `~/.npmrc`, VS Code's live `settings.json` mutations), internal hostnames, and herdr-mirror `hosts.toml` — this repo is public. `install.sh` bootstraps a missing `.npmrc` from `.npmrc.example` but never replaces an existing machine-local file.

**Principle**: Follow XDG Base Directory Specification (`.config/`) by default. For CLI tools that do not respect XDG paths, create a dedicated top-level directory named after the tool (e.g., `claude/` for `~/.claude/`).
