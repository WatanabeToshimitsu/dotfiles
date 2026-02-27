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

autoload -Uz compinit
compinit -C

# Load a few important annexes, without Turbo
# (this is currently required for annexes)
zinit light-mode for \
    zdharma-continuum/zinit-annex-as-monitor \
    zdharma-continuum/zinit-annex-bin-gem-node \
    zdharma-continuum/zinit-annex-patch-dl \
    zdharma-continuum/zinit-annex-rust

# End of Zinit's installer chunk

# enhancd: fuzzy find cd "cd .." and "cd" and "cd -" is useful!
# git-open: when on local git repository, git-open is open remote repository on github(* not gitlab etc)
# anyframe: some convinient func
# tab-fzf: tab = fzf activate
# exa: colorful ls with icon and more.
# manydots: comvertor manydots to parent directry on interactive shell e.g. ... -> ../..
# zsh-completion: slow but rich kubectl completion

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
    zsh-users/zsh-history-substring-search

#####################
# SETOPT            #
#####################
export LANG=ja_JP.UTF-8 # * 日本語化
setopt auto_cd # * 入力したコマンドが存在せず、かつディレクトリ名と一致するなら、ディレクトリに cd する
setopt print_eight_bit # * 日本語ファイル名を表示可能にする
setopt extended_glob # * `man zshexpn` の FILENAME GENERATION を参照 # * 拡張 glob を有効にする
setopt auto_list # * 補完候補を一覧表示にする
setopt extended_history       # record timestamp of command in HISTFILE
setopt hist_expire_dups_first # delete duplicates first when HISTFILE size exceeds HISTSIZE
setopt hist_ignore_all_dups   # ignore duplicated commands history list
setopt hist_ignore_space      # ignore commands that start with space
setopt hist_verify            # show command with history expansion to user before running it
setopt inc_append_history     # add commands to HISTFILE in order of execution
setopt share_history          # share command history data
setopt always_to_end          # cursor moved to the end in full completion
setopt hash_list_all          # hash everything before completion
setopt automenu
setopt correct # spell correct
setopt vi
unsetopt beep
unsetopt completealiases      # こいつがONだとaliasに補完が付かない

# chpwd() exa --git --icons --classify --group-directories-first --color-scale
chpwd() { command -v lsd &>/dev/null && lsd || ls; }

###############
#   ZSTYLE    #
###############
# set list-colors to enable filename colorizing
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}
# preview directory's content with exa when completing cd
# zstyle ':fzf-tab:complete:cd:*' fzf-preview 'exa -1 --color=always $realpath'
# switch group using `,` and `.`
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

########################
# bookmarks
########################
# * cd ~hoge と入力すると /long/path/to/hogehoge ディレクトリに移動
hash -d dev=~/dev
hash -d ghq=~/ghq
hash -d zshrc=~/.zshrc
hash -d dotfiles=~/dotfiles

########################
# * cmd history setteing
########################
HISTFILE=$HOME/.zsh-history
HISTSIZE=30000
SAVEHIST=30000

#####################
# ENV VARIABLE      #
#####################
# * enable some cli
export PATH=$PATH:/usr/local/go/bin
export PATH=$PATH:$HOME/go/bin

export PATH="$PATH:/usr/local/bin/istio-1.7.4/bin"
export PATH="$HOME/utils:$PATH"
export PATH="$HOME/.deno/bin:$PATH"
export PATH="/Users/kz86n/.local/bin:$PATH"

# * Volta env
export VOLTA_HOME="$HOME/.volta"
export PATH="$VOLTA_HOME/bin:$PATH"

# * use utils
export PATH="$HOME/.shell-utils:$PATH"

# * Docker experimental func enable
export COMPOSE_DOCKER_CLI_BUILD=1
export DOCKER_BUILDKIT=1

export OPEN_BY_MY_EDITOR='code'

# java
export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"

# * REACT ENV
REACT_EDITOR=code

# fzf shortcuts customize
export FZF_CTRL_T_COMMAND='rg --files --hidden --follow --glob "!.git/*"'
export FZF_CTRL_T_OPTS='--preview "bat  --color=always --style=header,grid --line-range :100 {}"'

# workaround for puppeteer on m1 mac
# See: https://github.com/puppeteer/puppeteer/issues/6622#issuecomment-788199984
export PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
export PUPPETEER_EXECUTABLE_PATH=$(command -v chromium)
#####################
# COLORING          #
#####################
autoload colors && colors

###############
# * key bind  #
###############
# * zsh-history-substring
source ~/.shell-utils/zsh-history-substrig-search.zsh
bindkey '^[[A' history-substring-search-up
bindkey '^[[B' history-substring-search-down

#########
# funcs
#########
# git-branch-prune (extracted to .shell-utils/git-branch-prune.sh)
source "$HOME/.shell-utils/git-branch-prune.sh"

#####################
# ALIASES           #
#####################
# * alias
alias vi='/usr/bin/vim'

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
alias gcode='${OPEN_BY_MY_EDITOR} $(ghq root)/$(ghq list | fzf --preview "bat --color=always --style=header,grid --line-range :80 $(ghq root)/{}/README.*")'

alias d='docker'
alias dc='docker-compose'

alias ff='fzf'

alias ghq-rm='ghq-rm.sh'

##################
# set completion #
##################
# NOTE: add fpath and source -> compdef -> compinit
mkdir -p ~/.zsh/completion
fpath=(~/.zsh/completion $fpath)

command -v gh &>/dev/null && eval "$(gh completion -s zsh)"

if type brew &>/dev/null
then
#   FPATH="$(brew --prefix)/share/zsh/site-functions:${FPATH}"
  FPATH="/opt/homebrew/share/zsh/site-functions:${FPATH}"
fi

[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

command -v wtp &>/dev/null && eval "$(wtp shell-init zsh)"

#################
# Depend on Env #
#################
# *  for private PC
# * kubeconfig
export KUBECONFIG=$KUBECONFIG:$HOME/.kube/config
kubeconfigs=$(echo ~/.kube/config.*)
export KUBECONFIG=${KUBECONFIG}:$(echo ${kubeconfigs// /:})

# * 1password
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

# Machine-specific overrides (not tracked in git)
[[ -f ~/.zshrc.local ]] && source ~/.zshrc.local

# oh-my-posh prompt theming
command -v oh-my-posh &>/dev/null && eval "$(oh-my-posh init zsh --config ~/oh-my-posh-theme/myconfig.omp.json)"

# Claude experimental agent teams feature
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
[[ -f ~/.safe-chain/scripts/init-posix.sh ]] && source ~/.safe-chain/scripts/init-posix.sh
