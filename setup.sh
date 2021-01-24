#!/bin/bash

echo "install brew"
which brew || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

eval $(/home/linuxbrew/.linuxbrew/bin/brew shellenv)

echo "run brew doctor..."
which brew && brew doctor

echo "run brew update..."
which brew && brew update

echo "brew is setup"

apps=(
  exa
  ghq
  fzf
  zsh
  git
  gh
)

for app in "${apps[@]}"; do
  which $app || brew install $app || brew upgrade $app
done

brew tap