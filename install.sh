#!/bin/bash
WHO=$(whoami)
echo ""
echo " ---------------"
echo "| Hello ${WHO}! |"
echo " ---------------"

echo "----------------------------------------------"
echo "Run apt/yum update..."
echo "----------------------------------------------"
apt-get update -y || yum update -y || dnf update -y
# Remove stale lock files if they exist (only needed when previous apt was interrupted)
[ -f /var/lib/dpkg/lock ] && sudo rm -f /var/lib/dpkg/lock
[ -f /var/lib/dpkg/lock-frontend ] && sudo rm -f /var/lib/dpkg/lock-frontend
[ -f /var/cache/apt/archives/lock ] && sudo rm -f /var/cache/apt/archives/lock

if [ $WHO != "root" ]; then
  echo "----------------------------------------------"
  echo "Before installing brew,"
  echo "Install liblary to install brew requirements"
  echo "----------------------------------------------"
  which brew || sudo apt-get install -y build-essential curl file git || sudo yum groupinstall -y 'Development Tools'
  sudo yum install -y curl file git
  sudo yum install -y libxcrypt-compat
  echo "----------------------------------------------"
  echo "Now, start installing brew"
  echo "----------------------------------------------"
  which brew || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

function installApp() {
  manager=$1
  app=$2

  echo "----------------------------------------------"
  echo "install ${app}"
  echo "----------------------------------------------"
  which $app || ${manager} install -y $app
}

function installApps() {
  manager=$1

  # locales-all should be installed first. See https://qiita.com/suzuki-navi/items/b5f066db181092543854
  apps=(
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
    installApp $manager $app
  done
}

function installAppsNeedsBrew() {
  apps=(
    gh
    ghq
  )

  for app in "${apps[@]}"; do
    echo "----------------------------------------------"
    echo "install ${app}"
    echo "----------------------------------------------"
    installApp brew $app
  done

}

TEST_BREW=$(which brew)
TEST_APT=$(which apt-get)
TEST_DNF=$(which dnf)
TEST_YUM=$(which yum)

if [ $TEST_BREW ] && [ $WHO != "root" ]; then
  echo "----------------------------------------------"
  echo "Brew was installed!!"
  echo "----------------------------------------------"
  eval '$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)'

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

elif [ $TEST_APT ]; then
  installApps apt-get

elif [ $TEST_DNF ]; then
  installApps dnf

elif [ $TEST_YUM ]; then
  installApps yum

fi

ln -fs ~/dotfiles/.* ~/

# Install fzf (prefer brew, fallback to git clone)
if ! which fzf > /dev/null 2>&1; then
  if which brew > /dev/null 2>&1; then
    brew install fzf
  else
    git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
    ~/.fzf/install --all
  fi
fi

# Install ghq (prefer brew, fallback to latest release binary)
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

TEST_GHCLI=$(which gh)
if [ ! $TEST_GHCLI ]; then
  echo "----------------------------------------------"
  echo "install github cli"
  echo "----------------------------------------------"
  if [ $TEST_APT ]; then
    apt-get install -y software-properties-common
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
    sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    apt-get update
    apt-get install -y gh
  elif [ $TEST_DNF ]; then
    dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo
    dnf install -y gh
  fi
fi

# for devcontainer
if [ -e ~/.ssh-hostmachine ]; then
  cp -r ~/.ssh-hostmachine/* ~/.ssh
fi

if [ -e ~/.npmrc-hostmachine ]; then
  cp ~/.npmrc-hostmachine ~/.npmrc
fi
