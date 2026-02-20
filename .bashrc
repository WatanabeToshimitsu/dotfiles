[ -f ~/.fzf.bash ] && source ~/.fzf.bash
source "$HOME/.cargo/env"

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"                   # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" # This loads nvm bash_completion
export VOLTA_HOME="$HOME/.volta"
export PATH="$VOLTA_HOME/bin:$PATH"

source /Users/kz86n/.docker/init-bash.sh || true # Added by Docker Desktop
export PATH=/Users/kz86n/Library/Python/3.10/bin:${PATH}


source ~/.safe-chain/scripts/init-posix.sh # Safe-chain bash initialization script
