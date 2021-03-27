#!/bin/bash

echo "At first, try to install brew"
echo "Install liblary to install brew requirements"
sudo apt update -y || apt update -y || sudo yum update -y ||  yum update -y
sudo rm -f /var/lib/dpkg/lock-frontend || rm -f /var/lib/dpkg/lock-frontend
sudo rmdir -f /var/lib/dpkg/ || rmdir -f /var/lib/dpkg/
sudo rm -f /var/lib/apt/lists/lock || rm -f /var/lib/apt/lists/lock
sudo rm -f /var/cache/apt/archives/lock || rm -f /var/cache/apt/archives/lock
sudo apt autoremove || apt autoremove
which brew || sudo apt install build-essential curl file git || apt install build-essential curl file git || sudo yum groupinstall; sudo yum install curl file git; sudo yum install libxcrypt-compat || yum groupinstall; sudo yum install curl file git; sudo yum install libxcrypt-compat
echo "Install brew"
which brew || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

apps=(
  git
  curl
  unzip
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
    which $app || sudo apt install -y $app || apt install -y $app
  done

elif [ $TEST_YUM ]; then
  for app in "${apps[@]}"; do
    which $app || sudo yum install -y $app || yum install -y $app
  done
fi

ln -fs ~/dotfiles/.* ~/
chsh -s /bin/zsh