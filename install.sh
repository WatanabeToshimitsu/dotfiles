#!/bin/bash

echo "At first, try to install brew"
echo "Install liblary to install brew requirements"
apt update -y || yum update -y
rm /var/lib/dpkg/lock
rm /var/lib/dpkg/lock-frontend
rm /var/cache/apt/archives/lock
which brew || apt install -y build-essential curl file git || yum groupinstall -y 'Development Tools'; yum install -y curl file git; yum install -y libxcrypt-compat
echo "Install brew"
which brew || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

apps=(
  vim
  git
  curl
  zip
  unzip
  tar
  cat
  ghq
  fzf
  zsh
  git
  gh
)

TEST_BREW=$(which brew)
TEST_APT=$(which apt)
TEST_YUM=$(which yum)
WHO=$(whoami)

if [ $TEST_BREW ] && [ $WHO != "root" ]; then
  echo "brew can ve installed!!"
  eval '$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)'

  echo "run brew doctor..."
  which brew && brew doctor

  echo "run brew update..."
  which brew && brew update

  echo "brew is setup"

  for app in "${apps[@]}"; do
    which $app || brew install -y $app || brew upgrade -y $app
  done

elif [ $TEST_APT ]; then
  for app in "${apps[@]}"; do
    which $app || apt install -y $app
  done

elif [ $TEST_YUM ]; then
  for app in "${apps[@]}"; do
    which $app || yum install -y $app
  done
fi

ln -fs ~/dotfiles/.* ~/
chown -R ${WHO}:${WHO} ~/.ssh/*
chown -R ${WHO}:${WHO} ~/.gitconfig