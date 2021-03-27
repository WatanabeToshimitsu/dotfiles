#!/bin/bash
WHO=$(whoami)

echo "Hello ${WHO}!"
apt-get update -y || yum update -y
rm /var/lib/dpkg/lock
rm /var/lib/dpkg/lock-frontend
rm /var/cache/apt/archives/lock

if [ $WHO != "root" ]; then
  echo "Before installing brew,"
  echo "Install liblary to install brew requirements"
  which brew || apt-get install -y build-essential curl file git || yum groupinstall -y 'Development Tools'; yum install -y curl file git; yum install -y libxcrypt-compat
  echo "Now, start installing brew"
  which brew || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

apps=(
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
)

TEST_BREW=$(which brew)
TEST_APT=$(which apt-get)
TEST_YUM=$(which yum)

if [ $TEST_BREW ] && [ $WHO != "root" ]; then
  echo "Brew was installed!!"
  eval '$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)'

  echo "Run brew doctor..."
  which brew && brew doctor

  echo "Run brew update..."
  which brew && brew update

  echo "Brew is setup"

  for app in "${apps[@]}"; do
    which $app || brew install -y $app || brew upgrade -y $app
  done

elif [ $TEST_APT ]; then
  for app in "${apps[@]}"; do
    which $app || apt-get install -y $app
  done

elif [ $TEST_YUM ]; then
  for app in "${apps[@]}"; do
    which $app || yum install -y $app
  done
fi

ln -fs ~/dotfiles/.* ~/
chown -R ${WHO}:${WHO} ~/.ssh/*
chown -R ${WHO}:${WHO} ~/.gitconfig