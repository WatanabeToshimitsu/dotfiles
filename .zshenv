# XDG Base Directory Specification
# See: https://specifications.freedesktop.org/basedir-spec/latest/
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"

# .zshrc prepends to PATH unconditionally in several places, so nested shells
# accumulate copies. -U keeps the leftmost entry, which turns each prepend into
# a move-to-front instead of a duplicate.
typeset -U path

. "$HOME/.cargo/env"
