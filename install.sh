#!/usr/bin/env bash
set -euo pipefail

log_info()  { echo "[INFO]  $*"; }
log_warn()  { echo "[WARN]  $*" >&2; }
log_error() { echo "[ERROR] $*" >&2; }

backup_if_real_file() {
  local target="$1"
  if [ -e "$target" ] && [ ! -L "$target" ]; then
    local backup_dir="$HOME/.dotfiles-backup/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    mv "$target" "$backup_dir/$(basename "$target")"
    log_info "Backed up $(basename "$target") to $backup_dir/"
  fi
}

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"
WHO=$(whoami)

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

  log_info "----------------------------------------------"
  log_info "install ${app}"
  log_info "----------------------------------------------"
  if command -v "$app" > /dev/null 2>&1; then
    log_info "$app is already installed"
  else
    ${manager} install -y "$app"
  fi
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
    log_info "----------------------------------------------"
    log_info "install ${app}"
    log_info "----------------------------------------------"
    installApp brew "$app"
  done
}

setup_symlinks() {
  local dotfiles_dir="${1:-$DOTFILES_DIR}"
  local files=(
    .zshrc .bashrc .bash_profile .bash_logout
    .profile .zprofile .zshenv
    .vimrc .tmux.conf .gitconfig
    .huskyrc .npmrc
  )

  log_info "----------------------------------------------"
  log_info "Setting up symlinks..."
  log_info "----------------------------------------------"

  for file in "${files[@]}"; do
    if [ -f "$dotfiles_dir/$file" ]; then
      backup_if_real_file "$HOME/$file"
      ln -fs "$dotfiles_dir/$file" "$HOME/$file"
      echo "  linked: $file"
    fi
  done

  # .config/ subdirectory files (create parent dirs, then symlink individual files)
  local config_files=(
    .config/git/ignore
    .config/gh/config.yml
    .config/ghostty/config
  )

  for file in "${config_files[@]}"; do
    if [ -f "$dotfiles_dir/$file" ]; then
      mkdir -p "$HOME/$(dirname "$file")"
      backup_if_real_file "$HOME/$file"
      ln -fs "$dotfiles_dir/$file" "$HOME/$file"
      echo "  linked: $file"
    fi
  done

  # Claude Code global settings (claude/ → ~/.claude/)
  local claude_files=(
    CLAUDE.md
    RTK.md
    settings.json
    statusline.sh
    hooks/deny-check.sh
    hooks/notification.sh
    hooks/rtk-rewrite.sh
    hooks/validate-bash.sh
    rules/testing/vitest.md
    rules/typescript/documentation.md
    rules/typescript/type-safety.md
  )

  for file in "${claude_files[@]}"; do
    if [ -f "$dotfiles_dir/claude/$file" ]; then
      mkdir -p "$HOME/.claude/$(dirname "$file")"
      backup_if_real_file "$HOME/.claude/$file"
      ln -fs "$dotfiles_dir/claude/$file" "$HOME/.claude/$file"
      echo "  linked: .claude/$file"
    fi
  done

  # Directory symlinks: use -n to avoid following existing symlinks into the target
  # and rm -rf guard for the case where a real (non-symlink) directory exists
  if [ -d "$HOME/.shell-utils" ] && [ ! -L "$HOME/.shell-utils" ]; then rm -rf "$HOME/.shell-utils"; fi
  ln -fsn "$dotfiles_dir/.shell-utils" "$HOME/.shell-utils"
  echo "  linked: .shell-utils/"

  if [ -d "$HOME/oh-my-posh-theme" ] && [ ! -L "$HOME/oh-my-posh-theme" ]; then rm -rf "$HOME/oh-my-posh-theme"; fi
  ln -fsn "$dotfiles_dir/oh-my-posh-theme" "$HOME/oh-my-posh-theme"
  echo "  linked: oh-my-posh-theme/"

  # Validate symlinks
  log_info "Validating symlinks..."
  local errors=0
  for file in "${files[@]}"; do
    if [ -f "$dotfiles_dir/$file" ] && [ ! -L "$HOME/$file" ]; then
      log_error "Symlink validation failed: $HOME/$file"
      errors=$((errors + 1))
    fi
  done
  if [ "$errors" -eq 0 ]; then
    log_info "All symlinks validated successfully"
  else
    log_error "$errors symlink(s) failed validation"
  fi
}

install_fzf() {
  if ! command -v fzf > /dev/null 2>&1; then
    log_info "----------------------------------------------"
    log_info "install fzf"
    log_info "----------------------------------------------"
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
    log_info "----------------------------------------------"
    log_info "install ghq"
    log_info "----------------------------------------------"
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
    log_info "----------------------------------------------"
    log_info "install github cli"
    log_info "----------------------------------------------"
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
# macOS setup
# ========================================

setup_macos() {
  log_info "=========================================="
  log_info "Setting up macOS environment"
  log_info "=========================================="

  # Install Homebrew if not present
  if ! command -v brew > /dev/null 2>&1; then
    log_info "----------------------------------------------"
    log_info "Installing Homebrew..."
    log_info "----------------------------------------------"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi

  log_info "----------------------------------------------"
  log_info "Running brew bundle..."
  log_info "----------------------------------------------"
  brew bundle --file="$DOTFILES_DIR/Brewfile"

  setup_symlinks "$DOTFILES_DIR"
}

# ========================================
# Linux setup
# ========================================

setup_linux() {
  log_info "=========================================="
  log_info "Setting up Linux environment"
  log_info "=========================================="

  log_info "----------------------------------------------"
  log_info "Run apt/yum update..."
  log_info "----------------------------------------------"
  apt-get update -y || yum update -y || dnf update -y || true
  # Remove stale lock files if they exist (only needed when previous apt was interrupted)
  if [ -f /var/lib/dpkg/lock ]; then sudo rm -f /var/lib/dpkg/lock; fi
  if [ -f /var/lib/dpkg/lock-frontend ]; then sudo rm -f /var/lib/dpkg/lock-frontend; fi
  if [ -f /var/cache/apt/archives/lock ]; then sudo rm -f /var/cache/apt/archives/lock; fi

  if [ "$WHO" != "root" ]; then
    log_info "----------------------------------------------"
    log_info "Before installing brew,"
    log_info "Install library to install brew requirements"
    log_info "----------------------------------------------"
    if command -v brew > /dev/null 2>&1; then
      log_info "brew is already installed"
    else
      sudo apt-get install -y build-essential curl file git || sudo yum groupinstall -y 'Development Tools'
    fi
    sudo yum install -y curl file git 2>/dev/null
    sudo yum install -y libxcrypt-compat 2>/dev/null
    log_info "----------------------------------------------"
    log_info "Now, start installing brew"
    log_info "----------------------------------------------"
    if command -v brew > /dev/null 2>&1; then
      log_info "brew is already installed"
    else
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
  fi

  TEST_BREW=$(command -v brew 2>/dev/null)
  TEST_APT=$(command -v apt-get 2>/dev/null)
  TEST_DNF=$(command -v dnf 2>/dev/null)
  TEST_YUM=$(command -v yum 2>/dev/null)

  if [ "$TEST_BREW" ] && [ "$WHO" != "root" ]; then
    log_info "----------------------------------------------"
    log_info "Brew was installed!!"
    log_info "----------------------------------------------"
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

    log_info "----------------------------------------------"
    log_info "Run brew doctor..."
    log_info "----------------------------------------------"
    brew doctor

    log_info "----------------------------------------------"
    log_info "Run brew update..."
    log_info "----------------------------------------------"
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

OS="$(uname -s)"
case "$OS" in
  Darwin) setup_macos ;;
  Linux)  setup_linux ;;
  *)      echo "Unsupported OS: $OS"; exit 1 ;;
esac

echo ""
log_info "=========================================="
log_info "Setup complete!"
log_info "=========================================="
