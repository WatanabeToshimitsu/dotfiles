# Shared environment setup
[ -f ~/.shell-common ] && . ~/.shell-common

export BASH_COMPLETION_COMPAT_DIR="/usr/local/etc/bash_completion.d"
[[ -r "/opt/homebrew/etc/profile.d/bash_completion.sh" ]] && . "/opt/homebrew/etc/profile.d/bash_completion.sh"

source /Users/kz86n/.docker/init-bash.sh || true # Added by Docker Desktop
