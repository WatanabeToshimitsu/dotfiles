#!/bin/bash
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

  echo "----------------------------------------------"
  echo "install ${app}"
  echo "----------------------------------------------"
  which "$app" || ${manager} install -y "$app"
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
    echo "----------------------------------------------"
    echo "install ${app}"
    echo "----------------------------------------------"
    installApp brew "$app"
  done
}

setup_symlinks() {
  local dotfiles_dir="${1:-$DOTFILES_DIR}"
  local files=(
    .zshrc .bashrc .bash_profile .bash_logout
    .profile .zprofile .zshenv
    .vimrc .tmux.conf .gitconfig
  )

  echo "----------------------------------------------"
  echo "Setting up symlinks..."
  echo "----------------------------------------------"

  for file in "${files[@]}"; do
    if [ -f "$dotfiles_dir/$file" ]; then
      ln -fs "$dotfiles_dir/$file" "$HOME/$file"
      echo "  linked: $file"
    fi
  done

  # .shell-utils directory
  ln -fs "$dotfiles_dir/.shell-utils" "$HOME/.shell-utils"
  echo "  linked: .shell-utils/"

  # oh-my-posh theme directory
  ln -fs "$dotfiles_dir/oh-my-posh-theme" "$HOME/oh-my-posh-theme"
  echo "  linked: oh-my-posh-theme/"
}

install_fzf() {
  if ! which fzf > /dev/null 2>&1; then
    echo "----------------------------------------------"
    echo "install fzf"
    echo "----------------------------------------------"
    if which brew > /dev/null 2>&1; then
      brew install fzf
    else
      git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
      ~/.fzf/install --all
    fi
  fi
}

install_ghq() {
  if ! which ghq > /dev/null 2>&1; then
    echo "----------------------------------------------"
    echo "install ghq"
    echo "----------------------------------------------"
    if which brew > /dev/null 2>&1; then
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
  if ! which gh > /dev/null 2>&1; then
    echo "----------------------------------------------"
    echo "install github cli"
    echo "----------------------------------------------"
    if which apt-get > /dev/null 2>&1; then
      apt-get install -y software-properties-common
      curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
      sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
      apt-get update
      apt-get install -y gh
    elif which dnf > /dev/null 2>&1; then
      dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo
      dnf install -y gh
    fi
  fi
}

# ========================================
# macOS setup
# ========================================

setup_macos() {
  echo "=========================================="
  echo "Setting up macOS environment"
  echo "=========================================="

  # Install Homebrew if not present
  if ! which brew > /dev/null 2>&1; then
    echo "----------------------------------------------"
    echo "Installing Homebrew..."
    echo "----------------------------------------------"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi

  echo "----------------------------------------------"
  echo "Running brew bundle..."
  echo "----------------------------------------------"
  brew bundle --file="$DOTFILES_DIR/Brewfile"

  setup_symlinks "$DOTFILES_DIR"
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
    which brew || sudo apt-get install -y build-essential curl file git || sudo yum groupinstall -y 'Development Tools'
    sudo yum install -y curl file git 2>/dev/null
    sudo yum install -y libxcrypt-compat 2>/dev/null
    echo "----------------------------------------------"
    echo "Now, start installing brew"
    echo "----------------------------------------------"
    which brew || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  fi

  TEST_BREW=$(which brew 2>/dev/null)
  TEST_APT=$(which apt-get 2>/dev/null)
  TEST_DNF=$(which dnf 2>/dev/null)
  TEST_YUM=$(which yum 2>/dev/null)

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
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
