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

### Secrets

Machine-local secrets also live in `~/.zshrc.local`, generated from
[`templates/zshrc.local.tpl`](templates/zshrc.local.tpl) by running
`dotfiles-secrets.sh` (on `PATH` after `install.sh`). Rendering requires a
signed-in [1Password CLI](https://developer.1password.com/docs/cli/) (`op`);
the resulting file is never tracked by this repo. The script refuses to replace
an existing file unless passed `--force`, writes with mode `0600`, and preserves
the old file if 1Password cannot render the template. Keep only `op://`
references—not plaintext secrets—in the tracked template.

Pushover notifications are disabled unless both `PUSHOVER_API_TOKEN` and
`PUSHOVER_USER_KEY` are present in the environment. Enabling them sends the
Claude notification text to the Pushover API. Store these values only in the
machine-local `~/.zshrc.local`; notification failures and timeouts do not block
Claude.

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

Normal `claude` uses Auto mode for trusted, routine work; the classifier is not an
OS sandbox, and bypass permissions is disabled. Use the canary for sensitive
repositories or data, unfamiliar external code, or stronger filesystem and
network isolation. The trial blocks common credentials, does not pre-allow
package caches or registries, and keeps only the known `gh` and Docker
compatibility exceptions. See [`claude/SANDBOX.md`](claude/SANDBOX.md) for the
boundary, verification, and rollback.

## Claude Auto Memory

Claude Code's repository-scoped auto memory is the only active project-learning
path. It is shared across worktrees without a custom hook. See
[`claude/AUTO-MEMORY.md`](claude/AUTO-MEMORY.md) for the verified behavior and
legacy-data policy.

## Loop Contracts

A scheduled or repeated agent run may discover work with user-level defaults,
but it may change a repository only when that repository has an approved Loop
contract. Without a contract, or while its status is `draft`, the run must stay
read-only and hand the candidate work to a person.

| User-level dotfiles provide | Each project must decide |
| --- | --- |
| A safe read-only fallback when no contract exists | Which work may be discovered and how to rank it |
| The contract template and runner-selection guidance | Allowed files, commands, services, and explicit forbidden areas |
| Common worktree, implementer, verifier, and handoff practices | Tests, CI checks, logs, and artifacts that prove success |
| A requirement to record why a run stopped and where it can resume | Time, round, usage, and risk limits |
| No automatic merge, production operation, or secret change | The Issue, PR, or file that stores durable state |

Choose the execution surface from the work rather than treating the runners as
interchangeable:

| Need | Execution surface |
| --- | --- |
| Poll briefly while an existing Claude Code session stays open | Claude Code [`/loop`](https://code.claude.com/docs/en/scheduled-tasks) |
| Read local files while the Mac and desktop app can remain running | A local desktop scheduled task in [Claude Code](https://code.claude.com/docs/en/desktop-scheduled-tasks) or the [OpenAI desktop app](https://learn.chatgpt.com/docs/automations) |
| Keep running while the Mac is off | A Claude Code [Routine](https://code.claude.com/docs/en/routines) |
| React to a PR, CI, or another repository event | [GitHub Actions](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflows) |

Cloud and CI runners must not depend on uncommitted local state. When a local
desktop task is approved to write, give each run an isolated worktree instead
of the shared checkout.

Copy [`templates/loop-contract.md`](templates/loop-contract.md) into a project
and fill it in before enabling writes. The
[`dotfiles` example](docs/dotfiles-loop-contract.example.md) shows the minimum
specificity expected for one bounded delivery run. Projects that do not adopt
the template do not permit automated changes.

## Headroom Proxy

`install.sh` installs Headroom 0.36.5 with `uv` and maintains a user-scoped
proxy on port 8787. The proxy runs as a supervised native process, so launchd
starts it at login and restarts it if it dies; no container runtime is
involved. Target selection is left to auto detection, so every supported tool
that is installed gets configured. The beta output shaper is enabled, and new
shell sessions route Claude Code and Codex through the proxy.

A 10% holdout leaves one conversation in ten unshaped as a control arm, so
`headroom output-savings` reports `MEASURED` instead of `ESTIMATED`. That costs
the shaping on those conversations. Without it the reported reduction is
compared against a synthetic baseline and comes back with a confidence band
wider than the reduction itself, which is no basis for deciding whether the
proxy earns its place. `dotfiles-doctor.sh` prints the reported method next to
the reduction, and the holdout below it.

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

Rerunning `install.sh` migrates an existing Docker deployment to the
supervised native process instead of leaving a stale container behind. The
Docker preset is not used: it needs a running Docker daemon, tracks the
`:latest` image rather than the pinned version, and cannot restart itself from
inside the container.

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

## Public Repository Safety

The root `.gitignore` excludes machine-local tool state, `.env` variants, npm
credentials, and common private-key formats. Placeholder files such as
`.env.example` and `.npmrc.example` remain trackable.

Every pull request and push to `main` scans the complete Git history with the
checksum-verified Gitleaks version pinned in CI. `test/test-secret-scan.sh`
checks both sides of the boundary: a synthetic credential must be detected,
while placeholder-only configuration must pass. There are currently no
`.gitleaksignore` or custom allowlist exceptions; add any future exception as
narrowly as possible and document why it is safe.

GitHub push protection is the first remote guard and Gitleaks CI is the
repository-owned, reproducible check. A machine-local pre-commit scanner may be
used as extra protection, but this repository does not install or depend on a
global hook.

## External Dependency Policy

Code that CI or unattended setup executes is pinned where the repository can
verify it:

- GitHub Actions use full commit SHAs, with release tags left as comments for
  Renovate and reviewers. The `pin-actions` job rejects floating references.
- CI invokes `json5` at an exact npm version. Gitleaks and the Linux fallback
  download of `ghq` use exact releases and SHA-256 checksums. Headroom is also
  installed at an exact Python package version.

Some first-run bootstrap operations intentionally follow upstream. The
Homebrew installer runs only when Homebrew is absent; agent Skills, fzf, GitHub
CLI extensions, and language tool inventories are fetched only during an
explicit `install.sh` run and are skipped when already installed. Update these
through a reviewed `install.sh` or `Brewfile` run rather than adding a separate
commit-SHA registry for every Plugin or Skill.

The Claude status line remains on `@latest` by the maintainer's explicit choice
in #67, so it updates without repository changes. If it regresses, replace the
tag with the version reported by `npm view @owloops/claude-powerline version`,
verify it with a representative status-line payload, and commit that change.
