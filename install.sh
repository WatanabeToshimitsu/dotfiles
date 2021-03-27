#!/bin/bash
WHO=$(whoami)
echo ""
echo " ---------------"
echo "| Hello ${WHO}! |"
echo " ---------------"

echo "----------------------------------------------"
echo "Run apt/yum update..."
echo "----------------------------------------------"
apt-get update -y || yum update -y
rm /var/lib/dpkg/lock
rm /var/lib/dpkg/lock-frontend
rm /var/cache/apt/archives/lock

if [ $WHO != "root" ]; then
  echo "----------------------------------------------"
  echo "Before installing brew,"
  echo "Install liblary to install brew requirements"
  echo "----------------------------------------------"
  which brew || apt-get install -y build-essential curl file git || yum groupinstall -y 'Development Tools'; yum install -y curl file git; yum install -y libxcrypt-compat
  echo "----------------------------------------------"
  echo "Now, start installing brew"
  echo "----------------------------------------------"
  which brew || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

function installApp() {
  manager=$1
  # locales-all should be installed first. See https://qiita.com/suzuki-navi/items/b5f066db181092543854
  apps=(
    locales-all
    cat
    curl
    fzf
    gh
    ghq
    git
    tar
    unzip
    vim
    zip
    zsh
    tmux
    psmisc
    procps
  )

  for app in "${apps[@]}"; do
    echo "----------------------------------------------"
    echo "install ${app}"
    echo "----------------------------------------------"
    which $app || ${manager} install -y $app
  done
}

TEST_BREW=$(which brew)
TEST_APT=$(which apt-get)
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

  installApp brew

elif [ $TEST_APT ]; then
  installApp apt-get

elif [ $TEST_YUM ]; then
  instsllApp yum

fi

ln -fs ~/dotfiles/.* ~/
chown -R ${WHO}:${WHO} ~/.ssh/*
chown -R ${WHO}:${WHO} ~/.gitconfig