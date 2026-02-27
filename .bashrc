[ -f ~/.fzf.bash ] && source ~/.fzf.bash
# Shared environment setup
[ -f ~/.shell-common ] && . ~/.shell-common

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"                   # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" # This loads nvm bash_completion

source /Users/kz86n/.docker/init-bash.sh || true # Added by Docker Desktop
export PATH=/Users/kz86n/Library/Python/3.10/bin:${PATH}


source ~/.safe-chain/scripts/init-posix.sh # Safe-chain bash initialization script
