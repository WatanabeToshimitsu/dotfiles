# Added by Zinit's installer
if [[ ! -f $HOME/.local/share/zinit/zinit.git/zinit.zsh ]]; then
    print -P "%F{33} %F{220}Installing %F{33}ZDHARMA-CONTINUUM%F{220} Initiative Plugin Manager (%F{33}zdharma-continuum/zinit%F{220})…%f"
    command mkdir -p "$HOME/.local/share/zinit" && command chmod g-rwX "$HOME/.local/share/zinit"
    command git clone https://github.com/zdharma-continuum/zinit "$HOME/.local/share/zinit/zinit.git" && \
        print -P "%F{33} %F{34}Installation successful.%f%b" || \
        print -P "%F{160} The clone has failed.%f%b"
fi

source "$HOME/.local/share/zinit/zinit.git/zinit.zsh"
autoload -Uz _zinit
(( ${+_comps} )) && _comps[zinit]=_zinit

# Pre-compinit: fpath/FPATH expansion (must be before compinit)
mkdir -p ~/.zsh/completion
fpath=(~/.zsh/completion $fpath)
[[ -d /opt/homebrew/share/zsh/site-functions ]] && \
  FPATH="/opt/homebrew/share/zsh/site-functions:${FPATH}"

# gtr (fpath-based; strip its trailing duplicate compinit call)
command -v git-gtr &>/dev/null && \
  eval "$(git gtr completion zsh | perl -ne 'print unless /^autoload -Uz compinit/')"

autoload -Uz compinit
compinit -C

# Post-compinit: compdef-direct sources (require compinit to be loaded first)
command -v gh &>/dev/null && eval "$(gh completion -s zsh)"
command -v wtp &>/dev/null && eval "$(wtp shell-init zsh)"
# Reclaim stand-alone `gtr` from zsh's built-in _tr (GNU coreutils prefix map)
command -v git-gtr &>/dev/null && compdef _git-gtr gtr

# Annexes currently require loading without Turbo.
zinit light-mode for \
    zdharma-continuum/zinit-annex-as-monitor \
    zdharma-continuum/zinit-annex-bin-gem-node \
    zdharma-continuum/zinit-annex-patch-dl \
    zdharma-continuum/zinit-annex-rust

# End of Zinit's installer chunk

# enhancd: fuzzy find cd "cd .." and "cd" and "cd -" is useful!
# manydots: comvertor manydots to parent directry on interactive shell e.g. ... -> ../..

zinit wait"0a" lucid for \
    atinit"zicdreplay" \
        zdharma/fast-syntax-highlighting \
    blockf \
        zsh-users/zsh-completions \
    atload"!_zsh_autosuggest_start" \
        zsh-users/zsh-autosuggestions \
    atload'compdef k=kubectl' \
        nnao45/zsh-kubectl-completion \
    b4b4r07/enhancd \
    atload'enable-fzf-tab' \
        Aloxaf/fzf-tab \

zinit wait"0b" load lucid for \
    paulirish/git-open \
    mollifier/anyframe \
    autoload'#manydots-magic' \
        knu/zsh-manydots-magic \
    mollifier/cd-gitroot \
    atload'bindkey "^[[A" history-substring-search-up; bindkey "^[[B" history-substring-search-down' \
        zsh-users/zsh-history-substring-search

export LANG=ja_JP.UTF-8
setopt auto_cd
setopt print_eight_bit # * 日本語ファイル名を表示可能にする
setopt extended_glob # * `man zshexpn` の FILENAME GENERATION を参照
setopt auto_list
setopt extended_history       # record timestamp of command in HISTFILE
setopt hist_expire_dups_first
setopt hist_ignore_all_dups
setopt hist_ignore_space
setopt hist_verify            # show command with history expansion to user before running it
setopt inc_append_history
setopt share_history
setopt always_to_end          # cursor moved to the end in full completion
setopt hash_list_all
setopt automenu
setopt correct
setopt vi
unsetopt beep
unsetopt completealiases      # こいつがONだとaliasに補完が付かない

chpwd() { command -v lsd &>/dev/null && lsd || ls; }

zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}
zstyle ':fzf-tab:*' switch-group ',' '.'

zstyle ':completion:*' completer _expand _complete _ignored _approximate
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Z}'
zstyle ':completion:*' menu select=2
zstyle ':completion:*' select-prompt '%SScrolling active: current selection at %p%s'
zstyle ':completion:*:descriptions' format '-- %d --'
zstyle ':completion:*:processes' command 'ps -au$USER'
zstyle ':completion:complete:*:options' sort false
zstyle ':fzf-tab:complete:_zlua:*' query-string input
zstyle ':completion:*:*:*:*:processes' command "ps -u $USER -o pid,user,comm,cmd -w -w"
zstyle ':fzf-tab:complete:kill:argument-rest' extra-opts --preview=$extract'ps --pid=$in[(w)1] -o cmd --no-headers -w -w' --preview-window=down:3:wrap
zstyle ":completion:*:git-checkout:*" sort false

# * cd ~hoge と入力すると /long/path/to/hogehoge ディレクトリに移動
hash -d dev=~/dev
hash -d ghq=~/ghq
hash -d zshrc=~/.zshrc
hash -d dotfiles=~/dotfiles

HISTFILE=$HOME/.zsh-history
HISTSIZE=30000
SAVEHIST=30000

export PATH=$PATH:/usr/local/go/bin
export PATH=$PATH:$HOME/go/bin

export PATH="$PATH:/usr/local/bin/istio-1.7.4/bin"
export PATH="$HOME/utils:$PATH"
export PATH="$HOME/.deno/bin:$PATH"
export PATH="/Users/kz86n/.local/bin:$PATH"

# * shared env (Volta, Cargo) — POSIX file shared with bash/sh
. "$HOME/.shell-common"

export PATH="$HOME/.shell-utils:$PATH"

export COMPOSE_DOCKER_CLI_BUILD=1
export DOCKER_BUILDKIT=1

export OPEN_BY_MY_EDITOR='code'

export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"

REACT_EDITOR=code

export FZF_CTRL_T_COMMAND='rg --files --hidden --follow --glob "!.git/*"'
export FZF_CTRL_T_OPTS='--preview "bat  --color=always --style=header,grid --line-range :100 {}"'

autoload colors && colors

source ~/.shell-utils/git-branch-prune.zsh

alias vi='/usr/bin/vim'
command -v nvim &>/dev/null && alias vim='nvim'

if command -v lsd &>/dev/null; then
  alias ls='lsd'
  alias l='ls -l'
  alias la='ls -a'
  alias lla='ls -la'
  alias lt='ls --tree'
  alias tree='ls --tree'
fi

command -v bat &>/dev/null && alias cat='bat --paging=never'

command -v rg &>/dev/null && alias grep='rg'

# yazi wrapper: shell cwd follows yazi on exit
if command -v yazi &>/dev/null; then
  function y() {
    local tmp cwd
    tmp="$(mktemp -t "yazi-cwd.XXXXXX")"
    yazi "$@" --cwd-file="$tmp"
    IFS= read -r -d '' cwd <"$tmp"
    [ -n "$cwd" ] && [ "$cwd" != "$PWD" ] && builtin cd -- "$cwd"
    rm -f -- "$tmp"
  }
fi

alias bd='cd ..' # * need enhancd

alias hc='fzf-history-widget'

alias k='kubectl'
alias kc='kubectx'
alias kn='kubens'

alias g='git'
alias gb='git branch'
alias gpl='git pull'
alias gps='git push'
alias gsts='git status'
alias gco='git checkout'
alias gbd='cd-gitroot'
alias gcd='cd $(ghq root)/$(ghq list | fzf)'
alias gb-prune='git-branch-prune'
alias git-branch-open='git open' # * need paulirish/git-open
alias gbo='git-branch-open'
if command -v gh &>/dev/null; then
  alias git-pr-open='gh pr view --web'
  alias gpo='git-pr-open'
fi
alias gcode='${OPEN_BY_MY_EDITOR} $(ghq root)/$(ghq list | fzf --preview "bat --color=always --style=header,grid --line-range :80 $(ghq root)/{}/README.*")'
if command -v nvim &>/dev/null; then
  function gvim() {
    local repo
    repo="$(ghq list | fzf --preview "bat --color=always --style=header,grid --line-range :80 $(ghq root)/{}/README.*")" || return
    [ -n "$repo" ] && builtin cd -- "$(ghq root)/$repo" && nvim
  }
fi

alias d='docker'
alias dc='docker-compose'

alias ff='fzf'

alias ghq-rm='ghq-rm.sh'

# NOTE: must stay AFTER `setopt vi` so ^I (Tab) binding lands on viins keymap
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

#################
# Depend on Env #
#################
# *  for private PC
export KUBECONFIG=$KUBECONFIG:$HOME/.kube/config
kubeconfigs=$(echo ~/.kube/config.*)
export KUBECONFIG=${KUBECONFIG}:$(echo ${kubeconfigs// /:})

[[ -S "$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock" ]] && \
  export SSH_AUTH_SOCK="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"

[[ -f "$HOME/.docker/init-zsh.sh" ]] && source "$HOME/.docker/init-zsh.sh"
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
pyenv() {
  unfunction pyenv
  eval "$(command pyenv init -)"
  pyenv "$@"
}
python() {
  unfunction python pyenv
  eval "$(command pyenv init -)"
  python "$@"
}

command -v safe-rm &>/dev/null && alias rm='safe-rm'
export PATH="$HOME/.local/bin:$PATH"

command -v oh-my-posh &>/dev/null && eval "$(oh-my-posh init zsh --config ~/oh-my-posh-theme/myconfig.omp.json)"

export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
[[ -f ~/.safe-chain/scripts/init-posix.sh ]] && source ~/.safe-chain/scripts/init-posix.sh

# Editor: nvim when available (used by direnv, yazi opener, herdr prefix+e)
if command -v nvim &>/dev/null; then
  export EDITOR=nvim
else
  export EDITOR=vim
fi
eval "$(direnv hook zsh)"

. ~/.sky/.sky-complete.zsh

# herdr: vim-herdr-navigation passthrough — node TUIs (Claude Code etc.) keep
# their own ctrl+h/j/k/l; leave those panes with prefix+h/j/k/l instead.
# Read by the herdr server at launch (restart herdr to apply changes).
export HERDR_NAV_PASSTHROUGH_RE='^node$'

# zoxide: frecency-based jump via `z`/`zi` (cd itself stays on enhancd)
# zinit ships a `zi` alias that would shadow zoxide's function; drop it
unalias zi 2>/dev/null
command -v zoxide &>/dev/null && eval "$(zoxide init zsh)"

# Machine-specific config (work/private hosts etc.) — never tracked in this repo
[ -f ~/.zshrc.local ] && source ~/.zshrc.local

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

# Tell me when the proxy configured above is down, instead of letting Claude Code
# and Codex fail against a dead ANTHROPIC_BASE_URL.
source ~/.shell-utils/headroom-proxy-check.zsh
headroom_proxy_check
