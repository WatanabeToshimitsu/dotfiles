#!/bin/bash

# echo "At first, try to install brew"
# echo "Install liblary to install brew requirements"
# sudo apt update || apt update || sudo yum update ||  yum update
# which brew || sudo apt install build-essential curl file git || apt install build-essential curl file git || sudo yum groupinstall; sudo yum install curl file git; sudo yum install libxcrypt-compat || yum groupinstall; sudo yum install curl file git; sudo yum install libxcrypt-compat
# echo "Install brew"
# which brew || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

apps=(
  exa
  ghq
  fzf
  zsh
  git
  gh
)

# TEST_BREW=$(which brew)
TEST_APT=$(which apt)
TEST_YUM=$(which yum)
# if [ $TEST_BREW ]; then
#   echo "brew can ve installed!!"
#   eval '$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)'

#   echo "run brew doctor..."
#   which brew && brew doctor

#   echo "run brew update..."
#   which brew && brew update

#   echo "brew is setup"

#   for app in "${apps[@]}"; do
#     which $app || brew install $app || brew upgrade $app
#   done

if [ $TEST_APT ]; then
  for app in "${apps[@]}"; do
    which $app || sudo apt install $app || apt install $app
  done

elif [ $TEST_YUM ]; then
  for app in "${apps[@]}"; do
    which $app || sudo yum install $app || yum install $app
  done
fi



ln -fs ~/dotfiles/.* ~/