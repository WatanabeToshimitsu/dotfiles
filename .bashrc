[ -f ~/.fzf.bash ] && source ~/.fzf.bash
. "$HOME/.shell-common"

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"                   # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" # This loads nvm bash_completion

source /Users/kz86n/.docker/init-bash.sh || true # Added by Docker Desktop
export PATH=/Users/kz86n/Library/Python/3.10/bin:${PATH}


source ~/.safe-chain/scripts/init-posix.sh # Safe-chain bash initialization script

# ROS2 Console configuration for better log output
export RCUTILS_COLORIZED_OUTPUT=1
export RCUTILS_CONSOLE_OUTPUT_FORMAT="[{severity} {time}] [{name}]: {message} ({function_name}() at {file_name}:{line_number})"
export GTEST_COLOR=1

# Ccache configuration for Autoware build
export CC="/usr/lib/ccache/gcc"
export CXX="/usr/lib/ccache/g++"
export CCACHE_DIR="/Users/kz86n/.cache/ccache/"
