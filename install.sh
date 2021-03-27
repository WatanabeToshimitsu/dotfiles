#!/bin/bash

echo "At first, try to install brew"
echo "Install liblary to install brew requirements"
sudo apt update -y || apt update -y || sudo yum update -y ||  yum update -y
which brew || sudo apt install build-essential curl file git || apt install build-essential curl file git || sudo yum groupinstall; sudo yum install curl file git; sudo yum install libxcrypt-compat || yum groupinstall; sudo yum install curl file git; sudo yum install libxcrypt-compat
echo "Install brew"
which brew || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

apps=(
  exa
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