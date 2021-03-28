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
rm /var/lib/dpkg/lock
rm /var/lib/dpkg/lock-frontend
rm /var/cache/apt/archives/lock

if [ $WHO != "root" ]; then
  echo "----------------------------------------------"
  echo "Before installing brew,"
  echo "Install liblary to install brew requirements"
  echo "----------------------------------------------"
  which brew || sudo apt-get install -y build-essential curl file git || sudo yum groupinstall -y 'Development Tools'; sudo yum install -y curl file git; sudo yum install -y libxcrypt-compat
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
    cat
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
  instsllApps dnf

elif [ $TEST_YUM ]; then
  instsllApps yum

fi

ln -fs ~/dotfiles/.* ~/

git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
~/.fzf/install --all

TEST_GHQ=$(which ghq)
GO_BIN_DIR=~/go/bin
if [ ! $TEST_GHQ ]; then
  echo "----------------------------------------------"
  echo "install ghq"
  echo "----------------------------------------------"
  GHQ_BUILD_DIR=~/.ghq-build
  mkdir -p $GHQ_BUILD_DIR
  cd $GHQ_BUILD_DIR
  curl -OL https://github.com/x-motemen/ghq/releases/download/v1.1.7/ghq_linux_amd64.zip
  unzip ghq_linux_amd64.zip
  mkdir -p $GO_BIN_DIR
  mv ${GHQ_BUILD_DIR}/ghq_linux_amd64/ghq $GO_BIN_DIR
  rm -fr GHQ_BUILD_DIR
fi

TEST_GHCLI=$(which gh)
if [ ! $TEST_GHCLI ]; then
  echo "----------------------------------------------"
  echo "install github cli"
  echo "----------------------------------------------"
  if [ $TEST_APT ]; then
    apt-get install -y software-properties-common
    apt-key adv --keyserver keyserver.ubuntu.com --recv-key C99B11DEB97541F0
    apt-add-repository https://cli.github.com/packages
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