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

# >>> headroom persistent env >>>
export HEADROOM_PORT="8787"
export HEADROOM_HOST="127.0.0.1"
export HEADROOM_MODE="cache"
export HEADROOM_BACKEND="anthropic"
export HEADROOM_TELEMETRY="off"
export HEADROOM_ROLLOUT_CHANNEL="beta"
export HEADROOM_OUTPUT_SHAPER="1"
export HEADROOM_OUTPUT_HOLDOUT="0.1"
export ANTHROPIC_BASE_URL="http://127.0.0.1:8787"
export ENABLE_TOOL_SEARCH="true"
export OPENAI_BASE_URL="http://127.0.0.1:8787/v1"
# <<< headroom persistent env <<<
