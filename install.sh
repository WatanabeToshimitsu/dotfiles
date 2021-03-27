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
    cat
    curl
    fzf
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
    installApp $manager $app
  done
}

function installAppsNeedsBrew() {
  apps=(
    gh
    ghq
  )

  for app in "${apps[@]}"; do
    installApp brew $app
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

  installApps brew
  installAppsNeedsBrew

elif [ $TEST_APT ]; then
  installApps apt-get

elif [ $TEST_YUM ]; then
  instsllApps yum

fi

ln -fs ~/dotfiles/.* ~/

# for devcontainer
chown -R ${WHO}:${WHO} ~/.ssh/*
chown ${WHO}:${WHO} ~/.gitconfig
chown ${WHO}:${WHO} ~/.npmrc