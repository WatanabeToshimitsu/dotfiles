#!/bin/bash
DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHO=$(whoami)
BACKUP_TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# shellcheck source=symlink-manifest.sh
source "$DOTFILES_DIR/symlink-manifest.sh"

echo ""
echo " ---------------"
echo "| Hello ${WHO}! |"
echo " ---------------"

# ========================================
# Shared helpers
# ========================================

installApp() {
  local manager=$1
  local app=$2

  echo "----------------------------------------------"
  echo "install ${app}"
  echo "----------------------------------------------"
  command -v "$app" || ${manager} install -y "$app"
}

installApps() {
  local manager=$1

  # locales-all should be installed first. See https://qiita.com/suzuki-navi/items/b5f066db181092543854
  local apps=(
    locales-all
    build-essential
    curl
    file
    git
    jq
    less
    procps
    psmisc
    tar
    tmux
    unzip
    vim
    zip
    zsh
  )

  for app in "${apps[@]}"; do
    installApp "$manager" "$app"
  done
}

installAppsNeedsBrew() {
  local apps=(
    bat
    gh
    ghq
    lsd
    oh-my-posh
    ripgrep
  )

  for app in "${apps[@]}"; do
    echo "----------------------------------------------"
    echo "install ${app}"
    echo "----------------------------------------------"
    installApp brew "$app"
  done
}

# Back up a real (non-symlink) file before it gets replaced by a symlink.
# Moves it to ~/.dotfiles-backup/<run-timestamp>/<same relative path>.
backup_if_real_file() {
  local target=$1
  [ -e "$target" ] && [ ! -L "$target" ] || return 0

  local rel_path=${target#"$HOME/"}
  local dest="$HOME/.dotfiles-backup/$BACKUP_TIMESTAMP/$rel_path"
  mkdir -p "$(dirname "$dest")"
  mv "$target" "$dest"
  echo "  backed up: $rel_path"
}

setup_npmrc() {
  local dotfiles_dir="$1"
  local target="$HOME/.npmrc"
  local retired_target="$dotfiles_dir/.npmrc"
  local template="$dotfiles_dir/.npmrc.example"

  if [ -L "$target" ]; then
    if [ "$(readlink "$target")" != "$retired_target" ]; then
      echo "  exists: .npmrc (foreign symlink left unmanaged)"
      return 0
    fi
    rm "$target"
    echo "  removed retired link: .npmrc"
  elif [ -e "$target" ]; then
    echo "  exists: .npmrc (machine-local file left unchanged)"
    return 0
  fi

  if [ -f "$template" ]; then
    cp "$template" "$target"
    chmod 600 "$target"
    echo "  bootstrapped: .npmrc (machine-local)"
  fi
}

setup_symlinks() {
  local dotfiles_dir="${1:-$DOTFILES_DIR}"

  echo "----------------------------------------------"
  echo "Setting up symlinks..."
  echo "----------------------------------------------"

  for file in "${MANIFEST_FILES[@]}"; do
    if [ -f "$dotfiles_dir/$file" ]; then
      backup_if_real_file "$HOME/$file"
      ln -fs "$dotfiles_dir/$file" "$HOME/$file"
      echo "  linked: $file"
    fi
  done

  setup_npmrc "$dotfiles_dir"

  # .config/ subdirectory files (create parent dirs, then symlink individual files)
  for file in "${MANIFEST_CONFIG_FILES[@]}"; do
    if [ -f "$dotfiles_dir/$file" ]; then
      mkdir -p "$HOME/$(dirname "$file")"
      backup_if_real_file "$HOME/$file"
      ln -fs "$dotfiles_dir/$file" "$HOME/$file"
      echo "  linked: $file"
    fi
  done

  # Claude Code global settings (claude/ → ~/.claude/)
  for file in "${MANIFEST_CLAUDE_FILES[@]}"; do
    if [ -f "$dotfiles_dir/claude/$file" ]; then
      mkdir -p "$HOME/.claude/$(dirname "$file")"
      backup_if_real_file "$HOME/.claude/$file"
      ln -fs "$dotfiles_dir/claude/$file" "$HOME/.claude/$file"
      echo "  linked: .claude/$file"
    fi
  done

  local obsolete_file obsolete_target
  for obsolete_file in "${MANIFEST_CLAUDE_OBSOLETE_FILES[@]}"; do
    obsolete_target="$HOME/.claude/$obsolete_file"
    if [ -L "$obsolete_target" ] && [ "$(readlink "$obsolete_target")" = "$dotfiles_dir/claude/$obsolete_file" ]; then
      rm "$obsolete_target"
      echo "  removed obsolete link: .claude/$obsolete_file"
    fi
  done

  # Directory symlinks: use -n to avoid following existing symlinks into the target
  # and rm -rf guard for the case where a real (non-symlink) directory exists
  [ -d "$HOME/.shell-utils" ] && [ ! -L "$HOME/.shell-utils" ] && rm -rf "$HOME/.shell-utils"
  ln -fsn "$dotfiles_dir/.shell-utils" "$HOME/.shell-utils"
  echo "  linked: .shell-utils/"

  [ -d "$HOME/oh-my-posh-theme" ] && [ ! -L "$HOME/oh-my-posh-theme" ] && rm -rf "$HOME/oh-my-posh-theme"
  ln -fsn "$dotfiles_dir/oh-my-posh-theme" "$HOME/oh-my-posh-theme"
  echo "  linked: oh-my-posh-theme/"

  # Neovim config (LazyVim): whole-directory symlink; back up any real dir first
  if [ -d "$HOME/.config/nvim" ] && [ ! -L "$HOME/.config/nvim" ]; then
    mkdir -p "$HOME/.dotfiles-backup/$BACKUP_TIMESTAMP/.config"
    mv "$HOME/.config/nvim" "$HOME/.dotfiles-backup/$BACKUP_TIMESTAMP/.config/nvim"
    echo "  backed up: .config/nvim"
  fi
  mkdir -p "$HOME/.config"
  ln -fsn "$dotfiles_dir/.config/nvim" "$HOME/.config/nvim"
  echo "  linked: .config/nvim/"
}

# Restore Neovim plugins pinned by lazy-lock.json (first run also clones lazy.nvim)
bootstrap_neovim() {
  command -v nvim > /dev/null 2>&1 || return 0
  echo "----------------------------------------------"
  echo "Bootstrapping Neovim plugins (lazy.nvim restore)..."
  echo "----------------------------------------------"
  nvim --headless "+Lazy! restore" +qa
}

install_fzf() {
  if ! command -v fzf > /dev/null 2>&1; then
    echo "----------------------------------------------"
    echo "install fzf"
    echo "----------------------------------------------"
    if command -v brew > /dev/null 2>&1; then
      brew install fzf
    else
      git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
      ~/.fzf/install --all
    fi
  fi
}

install_ghq() {
  if ! command -v ghq > /dev/null 2>&1; then
    echo "----------------------------------------------"
    echo "install ghq"
    echo "----------------------------------------------"
    if command -v brew > /dev/null 2>&1; then
      brew install ghq
    else
      GO_BIN_DIR=~/go/bin
      GHQ_BUILD_DIR=~/.ghq-build
      GHQ_VERSION=$(curl -s https://api.github.com/repos/x-motemen/ghq/releases/latest | grep '"tag_name"' | sed -E 's/.*"v([^"]+)".*/\1/')
      mkdir -p "$GHQ_BUILD_DIR"
      cd "$GHQ_BUILD_DIR" || exit
      curl -OL "https://github.com/x-motemen/ghq/releases/download/v${GHQ_VERSION}/ghq_linux_amd64.zip"
      unzip ghq_linux_amd64.zip
      mkdir -p "$GO_BIN_DIR"
      mv "${GHQ_BUILD_DIR}/ghq_linux_amd64/ghq" "$GO_BIN_DIR"
      rm -fr "$GHQ_BUILD_DIR"
      cd ~ || exit
    fi
  fi
}

install_gh_cli() {
  if ! command -v gh > /dev/null 2>&1; then
    echo "----------------------------------------------"
    echo "install github cli"
    echo "----------------------------------------------"
    if command -v apt-get > /dev/null 2>&1; then
      apt-get install -y software-properties-common
      curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
      sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
      apt-get update
      apt-get install -y gh
    elif command -v dnf > /dev/null 2>&1; then
      dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo
      dnf install -y gh
    fi
  fi
}

# ========================================
# launchd agents (macOS)
# ========================================
# Weekly dotfiles-doctor drift check; notifies only when warnings are found.
# The plist is generated here (not stored in the repo) so $HOME is baked in.

setup_launchd() {
  [ "$(uname -s)" = "Darwin" ] || return 0

  local label="com.kz86n.dotfiles-doctor"
  local plist="$HOME/Library/LaunchAgents/$label.plist"

  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$HOME/.shell-utils/dotfiles-doctor.sh</string>
    <string>--notify</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>1</integer>
    <key>Hour</key><integer>10</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/dotfiles-doctor.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/dotfiles-doctor.log</string>
</dict>
</plist>
EOF

  launchctl bootout "gui/$(id -u)/$label" 2> /dev/null || :
  if launchctl bootstrap "gui/$(id -u)" "$plist"; then
    echo "  loaded: $label (weekly Mon 10:00)"
  else
    echo "  failed: launchctl bootstrap $label"
  fi
}

# ========================================
# CLI tool inventories (gh extensions, pipx, volta)
# ========================================
# Idempotent: skips anything already installed.

setup_cli_tools() {
  echo "----------------------------------------------"
  echo "Installing CLI tool inventories..."
  echo "----------------------------------------------"

  if command -v gh > /dev/null 2>&1 && gh auth status > /dev/null 2>&1; then
    local ext
    for ext in seachicken/gh-poi github/gh-stack; do
      if gh extension list 2>/dev/null | grep -q "$ext"; then
        echo "  exists: gh extension $ext"
      else
        gh extension install "$ext" || echo "  failed: gh extension $ext"
      fi
    done
  else
    echo "  skipped gh extensions (gh missing or unauthenticated)"
  fi

  if command -v pipx > /dev/null 2>&1; then
    local tool
    for tool in aws-sam-cli cfn-lint poetry; do
      if pipx list --short 2>/dev/null | grep -q "^$tool "; then
        echo "  exists: pipx $tool"
      else
        pipx install "$tool" || echo "  failed: pipx $tool"
      fi
    done
  else
    echo "  skipped pipx tools (pipx not found)"
  fi

  if command -v volta > /dev/null 2>&1; then
    if volta which node > /dev/null 2>&1; then
      echo "  exists: volta node toolchain"
    else
      volta install node || echo "  failed: volta install node"
    fi

    local node_tool binary
    for node_tool in typescript typescript-language-server; do
      case "$node_tool" in
        typescript) binary=tsc ;;
        *) binary="$node_tool" ;;
      esac

      if command -v "$binary" > /dev/null 2>&1; then
        echo "  exists: volta $node_tool"
      else
        volta install "$node_tool" || echo "  failed: volta install $node_tool"
      fi
    done
  fi

  if command -v uv > /dev/null 2>&1; then
    if command -v headroom > /dev/null 2>&1 \
      && headroom --version 2>/dev/null | grep -q 'version 0\.36\.5$'; then
      echo "  exists: uv tool headroom-ai 0.36.5"
    else
      uv tool install --force "headroom-ai==0.36.5" || echo "  failed: uv tool headroom-ai"
    fi
  else
    echo "  skipped headroom-ai (uv not found)"
  fi
}

# ========================================
# Headroom persistent Claude proxy
# ========================================
# Recreates the user-scoped deployment when missing or when the persisted
# output-shaper settings drift. Prefer Docker and fall back to a native task.

setup_headroom() {
  if ! command -v headroom > /dev/null 2>&1; then
    echo "  skipped Headroom deployment (headroom not found)"
    return 0
  fi

  local manifest="$HOME/.headroom/deploy/default/manifest.json"
  local preset runtime
  if command -v docker > /dev/null 2>&1 && docker info > /dev/null 2>&1; then
    preset=persistent-docker
    runtime=docker
  else
    preset=persistent-task
    runtime=python
  fi

  if [ -f "$manifest" ] \
    && jq -e --arg preset "$preset" --arg runtime "$runtime" \
      '.provider_mode == "manual"
       and .targets == ["claude"]
       and .preset == $preset
       and .runtime_kind == $runtime
       and .base_env.HEADROOM_ROLLOUT_CHANNEL == "beta"
       and .base_env.HEADROOM_OUTPUT_SHAPER == "1"' \
      "$manifest" > /dev/null 2>&1; then
    echo "  exists: Headroom persistent Claude deployment ($preset)"
    if ! headroom install status --profile default 2>/dev/null | grep -q '^Status:.*running'; then
      if jq -e '.preset == "persistent-task"' "$manifest" > /dev/null 2>&1; then
        if [ -x "$HOME/.headroom/deploy/default/ensure-headroom.sh" ]; then
          echo "  recovering Headroom with scheduled-task watchdog"
          "$HOME/.headroom/deploy/default/ensure-headroom.sh" ||
            echo "  failed: Headroom scheduled-task recovery"
        else
          echo "  waiting for Headroom scheduled recovery"
        fi
      else
        headroom install start --profile default || echo "  failed: start Headroom deployment"
      fi
    fi
    return 0
  fi

  echo "----------------------------------------------"
  echo "Installing Headroom persistent Claude proxy..."
  echo "----------------------------------------------"
  headroom install apply \
    --preset "$preset" \
    --runtime "$runtime" \
    --scope user \
    --providers manual \
    --target claude \
    --profile default \
    --port 8787 \
    --backend anthropic \
    --mode cache \
    --no-telemetry \
    --env HEADROOM_ROLLOUT_CHANNEL=beta \
    --env HEADROOM_OUTPUT_SHAPER=1 \
    || echo "  failed: Headroom persistent Claude deployment"
}

# ========================================
# herdr integrations and plugins
# ========================================
# Idempotent: skips anything already installed/linked.

setup_herdr() {
  if ! command -v herdr > /dev/null 2>&1; then
    echo "  skipped herdr setup (herdr not found)"
    return 0
  fi

  echo "----------------------------------------------"
  echo "Setting up herdr integrations and plugins..."
  echo "----------------------------------------------"

  local integration
  for integration in claude codex; do
    if herdr integration status 2>/dev/null | grep -q "^${integration}: not installed"; then
      herdr integration install "$integration" || echo "  failed: integration $integration"
    else
      echo "  exists: integration $integration"
    fi
  done

  # repo:plugin_id pairs (id is what `herdr plugin list` reports)
  local plugins=(
    "paulbkim-dev/vim-herdr-navigation:vim-herdr-navigation"
    "persiyanov/herdr-reviewr:persiyanov.reviewr"
    "nikok6/herdr-mirror:mirror"
  )
  local installed entry repo id
  installed=$(herdr plugin list 2>/dev/null)
  for entry in "${plugins[@]}"; do
    repo="${entry%%:*}"
    id="${entry##*:}"
    if printf '%s' "$installed" | grep -q "^- ${id} "; then
      echo "  exists: plugin $id"
    else
      herdr plugin install "$repo" --yes || echo "  failed: plugin $repo"
    fi
  done

  if printf '%s' "$installed" | grep -q "^- kz86n.worktree-setup "; then
    echo "  exists: plugin kz86n.worktree-setup"
  else
    herdr plugin link "$DOTFILES_DIR/herdr-plugins/worktree-setup" ||
      echo "  failed: link worktree-setup"
  fi
}

# ========================================
# VS Code user config (macOS)
# ========================================
# keybindings.json is symlinked (never auto-modified by VS Code).
# settings.json is copied only when absent: VS Code rewrites it with
# machine-local state (SSH host maps etc.), so a symlink would leak
# that state back into this public repo.

setup_vscode() {
  local user_dir="$HOME/Library/Application Support/Code/User"
  [ -d "$user_dir" ] || return 0

  backup_if_real_file "$user_dir/keybindings.json"
  ln -fs "$DOTFILES_DIR/vscode/keybindings.json" "$user_dir/keybindings.json"
  echo "  linked: vscode keybindings.json"

  if [ ! -f "$user_dir/settings.json" ]; then
    cp "$DOTFILES_DIR/vscode/settings.json" "$user_dir/settings.json"
    echo "  copied: vscode settings.json (bootstrap)"
  fi
}

# ========================================
# Agent skills (npx skills / skills.sh)
# ========================================
# Reinstall global agent skills from exact commits when the repository lock changes.

setup_agent_skills() {
  local command_name
  for command_name in git jq npx; do
    if ! command -v "$command_name" > /dev/null 2>&1; then
      echo "  skipped agent skills ($command_name not found)"
      return 0
    fi
  done

  echo "----------------------------------------------"
  echo "Installing agent skills..."
  echo "----------------------------------------------"

  local lock_file="$DOTFILES_DIR/claude/dependencies.lock.json"
  local installed_lock="$HOME/.agents/.dotfiles-dependencies.lock.json"
  local missing_skill=0
  local skill

  if [ -f "$installed_lock" ] && cmp -s "$lock_file" "$installed_lock"; then
    while IFS= read -r skill; do
      if [ ! -e "$HOME/.agents/skills/$skill" ] \
        && [ ! -e "$HOME/.claude/skills/$skill" ]; then
        missing_skill=1
        break
      fi
    done < <(jq -r '.skills[].names[]' "$lock_file")
    if [ "$missing_skill" -eq 0 ]; then
      echo "  exists: agent skills match dependencies.lock.json"
      return 0
    fi
  fi

  local cli_version
  cli_version=$(jq -r '.skillsCli.version' "$lock_file")
  local source_entry repository commit checkout actual_commit
  local install_failed=0
  local staging_root staging_home staged_skill incoming_dir backup_dir
  local target legacy_target already_managed managed_skill
  local -a source_entries=()
  local -a expected_skills=()
  local -a managed_skills=()
  local -a backed_claude=()
  local -a backed_agents=()
  local -a installed_new=()

  while IFS= read -r source_entry; do
    source_entries+=("$source_entry")
  done < <(jq -c '.skills[]' "$lock_file")

  while IFS= read -r skill; do
    if [[ ! "$skill" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
      echo "  failed: unsafe skill name in dependencies.lock.json: $skill"
      return 1
    fi
    expected_skills+=("$skill")
    managed_skills+=("$skill")
  done < <(jq -r '.skills[].names[]' "$lock_file")

  if [ -f "$installed_lock" ] && jq -e '.skills | type == "array"' "$installed_lock" > /dev/null 2>&1; then
    while IFS= read -r skill; do
      [[ "$skill" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || continue
      already_managed=0
      for managed_skill in "${managed_skills[@]}"; do
        if [ "$managed_skill" = "$skill" ]; then
          already_managed=1
          break
        fi
      done
      [ "$already_managed" -eq 1 ] || managed_skills+=("$skill")
    done < <(jq -r '.skills[].names[]' "$installed_lock")
  fi

  staging_root=$(mktemp -d) || return 1
  staging_home="$staging_root/home"
  mkdir -p "$staging_home"

  for source_entry in "${source_entries[@]}"; do
    repository=$(printf '%s' "$source_entry" | jq -r '.repository')
    commit=$(printf '%s' "$source_entry" | jq -r '.commit')
    checkout="$staging_root/checkout-$commit"

    if ! git init --quiet "$checkout" \
      || ! git -C "$checkout" remote add origin "$repository" \
      || ! git -C "$checkout" fetch --quiet --depth 1 origin "$commit" \
      || ! git -C "$checkout" checkout --quiet --detach FETCH_HEAD; then
      echo "  failed: fetch $repository@$commit"
      install_failed=1
      continue
    fi

    actual_commit=$(git -C "$checkout" rev-parse HEAD 2>/dev/null)
    if [ "$actual_commit" != "$commit" ]; then
      echo "  failed: commit mismatch for $repository"
      install_failed=1
      continue
    fi

    while IFS= read -r skill; do
      if HOME="$staging_home" DO_NOT_TRACK=1 \
        npx -y "skills@$cli_version" add "$checkout" -g -y --copy \
          -s "$skill" -a claude-code < /dev/null; then
        echo "  installed: $skill@$commit"
      else
        echo "  failed: $skill@$commit"
        install_failed=1
      fi
    done < <(printf '%s' "$source_entry" | jq -r '.names[]')
  done

  for skill in "${expected_skills[@]}"; do
    staged_skill="$staging_home/.claude/skills/$skill"
    if [ ! -f "$staged_skill/SKILL.md" ]; then
      echo "  failed: staged skill is incomplete: $skill"
      install_failed=1
    fi
  done

  if [ "$install_failed" -ne 0 ]; then
    echo "  failed: existing agent skills were left unchanged"
    rm -rf "$staging_root"
    return 1
  fi

  mkdir -p "$HOME/.claude/skills" "$HOME/.agents/skills"
  incoming_dir="$HOME/.claude/skills/.dotfiles-incoming-$$"
  backup_dir="$HOME/.claude/skills/.dotfiles-backup-$$"
  mkdir -p "$incoming_dir" "$backup_dir/claude" "$backup_dir/agents"

  for skill in "${expected_skills[@]}"; do
    staged_skill="$staging_home/.claude/skills/$skill"
    if ! cp -R "$staged_skill" "$incoming_dir/$skill"; then
      echo "  failed: prepare replacement for $skill"
      rm -rf "$incoming_dir" "$backup_dir" "$staging_root"
      return 1
    fi
  done

  for skill in "${managed_skills[@]}"; do
    target="$HOME/.claude/skills/$skill"
    legacy_target="$HOME/.agents/skills/$skill"
    if [ -e "$target" ] || [ -L "$target" ]; then
      if ! mv "$target" "$backup_dir/claude/$skill"; then
        install_failed=1
        break
      fi
      backed_claude+=("$skill")
    fi
    if [ -e "$legacy_target" ] || [ -L "$legacy_target" ]; then
      if ! mv "$legacy_target" "$backup_dir/agents/$skill"; then
        install_failed=1
        break
      fi
      backed_agents+=("$skill")
    fi
  done

  if [ "$install_failed" -eq 0 ]; then
    for skill in "${expected_skills[@]}"; do
      if ! mv "$incoming_dir/$skill" "$HOME/.claude/skills/$skill"; then
        install_failed=1
        break
      fi
      installed_new+=("$skill")
    done
  fi

  if [ "$install_failed" -eq 0 ]; then
    mkdir -p "$HOME/.agents"
    if ! cp "$lock_file" "$installed_lock.tmp.$$" \
      || ! mv "$installed_lock.tmp.$$" "$installed_lock"; then
      install_failed=1
    fi
  fi

  if [ "$install_failed" -ne 0 ]; then
    echo "  failed: rolling back agent skill update"
    for skill in "${installed_new[@]}"; do
      mv "$HOME/.claude/skills/$skill" "$incoming_dir/$skill" 2>/dev/null || true
    done
    for skill in "${backed_claude[@]}"; do
      mv "$backup_dir/claude/$skill" "$HOME/.claude/skills/$skill" 2>/dev/null || true
    done
    for skill in "${backed_agents[@]}"; do
      mv "$backup_dir/agents/$skill" "$HOME/.agents/skills/$skill" 2>/dev/null || true
    done
    rm -f "$installed_lock.tmp.$$"
    rm -rf "$incoming_dir" "$backup_dir" "$staging_root"
    return 1
  fi

  rm -rf "$incoming_dir" "$backup_dir" "$staging_root"
  echo "  recorded: agent skills match dependencies.lock.json"
}

# ========================================
# macOS setup
# ========================================

setup_macos() {
  echo "=========================================="
  echo "Setting up macOS environment"
  echo "=========================================="

  # Install Homebrew if not present
  if ! command -v brew > /dev/null 2>&1; then
    echo "----------------------------------------------"
    echo "Installing Homebrew..."
    echo "----------------------------------------------"
    export NONINTERACTIVE=1
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi

  echo "----------------------------------------------"
  echo "Running brew bundle..."
  echo "----------------------------------------------"
  brew bundle --file="$DOTFILES_DIR/Brewfile"

  setup_symlinks "$DOTFILES_DIR"
  bootstrap_neovim
  setup_vscode
  setup_agent_skills || return 1
  setup_herdr
  setup_cli_tools
  setup_headroom
  setup_launchd
}

# ========================================
# Linux setup
# ========================================

setup_linux() {
  echo "=========================================="
  echo "Setting up Linux environment"
  echo "=========================================="

  echo "----------------------------------------------"
  echo "Run apt/yum update..."
  echo "----------------------------------------------"
  apt-get update -y || yum update -y || dnf update -y
  # Remove stale lock files if they exist (only needed when previous apt was interrupted)
  [ -f /var/lib/dpkg/lock ] && sudo rm -f /var/lib/dpkg/lock
  [ -f /var/lib/dpkg/lock-frontend ] && sudo rm -f /var/lib/dpkg/lock-frontend
  [ -f /var/cache/apt/archives/lock ] && sudo rm -f /var/cache/apt/archives/lock

  if [ "$WHO" != "root" ]; then
    echo "----------------------------------------------"
    echo "Before installing brew,"
    echo "Install library to install brew requirements"
    echo "----------------------------------------------"
    command -v brew || sudo apt-get install -y build-essential curl file git || sudo yum groupinstall -y 'Development Tools'
    sudo yum install -y curl file git 2>/dev/null
    sudo yum install -y libxcrypt-compat 2>/dev/null
    echo "----------------------------------------------"
    echo "Now, start installing brew"
    echo "----------------------------------------------"
    export NONINTERACTIVE=1
    command -v brew || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  fi

  TEST_BREW=$(command -v brew 2>/dev/null)
  TEST_APT=$(command -v apt-get 2>/dev/null)
  TEST_DNF=$(command -v dnf 2>/dev/null)
  TEST_YUM=$(command -v yum 2>/dev/null)

  if [ "$TEST_BREW" ] && [ "$WHO" != "root" ]; then
    echo "----------------------------------------------"
    echo "Brew was installed!!"
    echo "----------------------------------------------"
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

    echo "----------------------------------------------"
    echo "Run brew doctor..."
    echo "----------------------------------------------"
    brew doctor

    echo "----------------------------------------------"
    echo "Run brew update..."
    echo "----------------------------------------------"
    brew update

    installApps brew
    installAppsNeedsBrew

  elif [ "$TEST_APT" ]; then
    installApps apt-get

  elif [ "$TEST_DNF" ]; then
    installApps dnf

  elif [ "$TEST_YUM" ]; then
    installApps yum
  fi

  setup_symlinks "$DOTFILES_DIR"
  setup_agent_skills || return 1
  setup_herdr
  setup_cli_tools
  setup_headroom

  install_fzf
  install_ghq
  install_gh_cli

  # for devcontainer
  if [ -e ~/.ssh-hostmachine ]; then
    cp -r ~/.ssh-hostmachine/* ~/.ssh
  fi

  if [ -e ~/.npmrc-hostmachine ]; then
    cp ~/.npmrc-hostmachine ~/.npmrc
  fi
}

# ========================================
# Main
# ========================================

if [ "${DOTFILES_LIBRARY_MODE:-0}" = "1" ]; then
  return 0 2>/dev/null || exit 0
fi

if [ "${1:-}" = "--symlinks-only" ]; then
  setup_symlinks "$DOTFILES_DIR"
  echo ""
  echo "=========================================="
  echo "Symlink setup complete!"
  echo "=========================================="
  exit 0
fi

if [ "${1:-}" = "--headroom-only" ]; then
  setup_headroom
  echo ""
  echo "=========================================="
  echo "Headroom setup complete!"
  echo "=========================================="
  exit 0
fi

OS="$(uname -s)"
case "$OS" in
  Darwin) setup_macos || exit 1 ;;
  Linux)  setup_linux || exit 1 ;;
  *)      echo "Unsupported OS: $OS"; exit 1 ;;
esac

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
