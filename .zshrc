
# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

########################################
# zplug "mollifier/cd-gitroot"

### Added by Zinit's installer
if [[ ! -f $HOME/.zinit/bin/zinit.zsh ]]; then
    print -P "%F{33}▓▒░ %F{220}Installing %F{33}DHARMA%F{220} Initiative Plugin Manager (%F{33}zdharma/zinit%F{220})…%f"
    command mkdir -p "$HOME/.zinit" && command chmod g-rwX "$HOME/.zinit"
    command git clone https://github.com/zdharma/zinit "$HOME/.zinit/bin" && \
        print -P "%F{33}▓▒░ %F{34}Installation successful.%f%b" || \
        print -P "%F{160}▓▒░ The clone has failed.%f%b"
fi

source "$HOME/.zinit/bin/zinit.zsh"
autoload -Uz _zinit
(( ${+_comps} )) && _comps[zinit]=_zinit

# Load a few important annexes, without Turbo
# (this is currently required for annexes)
zinit light-mode for \
    zinit-zsh/z-a-rust \
    zinit-zsh/z-a-as-monitor \
    zinit-zsh/z-a-patch-dl \
    zinit-zsh/z-a-bin-gem-node

### End of Zinit's installer chunk

# power10k: rich and fast prompt
# enhancd: fuzzy find cd "cd .." and "cd" and "cd -" is useful!
# git-open: when on local git repository, git-open is open remote repository on github(* not gitlab etc)
# anyframe: some convinient func
# tab-fzf: tab = fzf activate
# exa: colorful ls with icon and more.
# manydots: comvertor manydots to parent directry on interactive shell e.g. ... -> ../..
# zsh-completion: slow but rich kubectl completion

zinit ice depth=1; zinit load romkatv/powerlevel10k
zinit wait"0a" lucid for \
    atinit"ZINIT[COMPINIT_OPTS]=-C; zicompinit; zicdreplay" \
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
    from"gh-r" as"program" mv"exa* -> exa" \
        ogham/exa \

zinit wait"0b" load lucid for \
    paulirish/git-open \
    mollifier/anyframe \
    atload'source ~/.zinit/plugins/zsh-users---zsh-history-substring-search/zsh-history-substring-search.zsh; bindkey "$terminfo[kcuu1]" history-substring-search-up; bindkey "$terminfo[kcud1]" history-substring-search-down' \
        zsh-users/zsh-history-substring-search \
    autoload'#manydots-magic' \
        knu/zsh-manydots-magic \
    mollifier/cd-gitroot \

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

chpwd() exa --git --icons --classify --group-directories-first --color-scale

###############
#   ZSTYLE    #
###############
# set list-colors to enable filename colorizing
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}
# preview directory's content with exa when completing cd
zstyle ':fzf-tab:complete:cd:*' fzf-preview 'exa -1 --color=always $realpath'
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
hash -d win=/mnt/c/
hash -d ghq=~/ghq
hash -d zshrc=~/.zshrc
hash -d dotfiles=~/dotfiles
hash -d desktop=/mnt/c/Users/kz86n/Desktop/

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
export PATH="$PATH:/usr/local/bin/istio-1.7.4/bin"
export PATH=$PATH:/usr/local/go/bin
export PATH=$PATH:$HOME/go/bin
export PATH=$PATH:$HOME/.fzf/bin
export PATH="$HOME/.poetry/bin:$PATH"
export PATH="$HOME/utils:$PATH"

# * Docker experimental func enable
export COMPOSE_DOCKER_CLI_BUILD=1
export DOCKER_BUILDKIT=1

# * kubeconfig
kubeconfigs=$(echo ~/.kube/config.*)
export KUBECONFIG=${KUBECONFIG}:$(echo ${kubeconfigs// /:})

export OPEN_BY_MY_EDITOR='code'

# * homebrew ENV
eval $(/home/linuxbrew/.linuxbrew/bin/brew shellenv)

# * nvm ENV
export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"


#####################
# COLORING          #
#####################
autoload colors && colors

###############
# * key bind  #
###############

#########
# funcs
#########
# * open in windows
if [[ $(uname -r) =~ microsoft ]]; then
    local Chrome='/mnt/c/Program\ Files/Google/Chrome/Application/chrome.exe'
    function open(){
        if [ $# -eq 0 ]; then
            echo "ERROR: get no input argument."
            echo "Please specify file-paths, URLs, googling-words"
            echo "open [file/path]"
            return 1
        fi
        for arg; do
            if [ -e "${arg}" ]; then
                cmd.exe /c start $(readlink -f ${arg} | xargs wslpath -w)
            elif [[ ${arg} =~ http ]]; then
                echo "${arg}" | xargs -I{} bash -c "${Chrome} '{}'"
            else
                echo "${arg}" | sed 's/ /+/g' | xargs -I{} bash -c "${Chrome} 'https://www.google.com/search?q={}'"
            fi
        done
    }
fi

# git prune
git-branch-prune() {
    PROTECT_BRANCHES='master|develop'

    if [ -z "$1" ]; then
        :
    else
        PROTECT_BRANCHES="${PROTECT_BRANCHES}|$1"
    fi

    # echo "fetch remote repository?(y/N): "
    # if read -q; then
    #     echo
    #     echo "fetching..."
    #     git fetch
    # else
    #     echo
    # fi

    echo "fetching..."
    git fetch

    echo
    echo "=== to be deleted ==="

    DELETE_BRANCH=`git branch -a --merged | egrep -v "\*|${PROTECT_BRANCHES}"`
    echo ${DELETE_BRANCH}

    echo
    echo "=== to be protected ( regex: ${PROTECT_BRANCHES} )==="
    git branch -a --merged | egrep "\*|${PROTECT_BRANCHES}"

    echo
    echo "delete branches?(y/N): "

    if read -q; then
        echo
        echo "deleting..."
        git fetch --prune
        git branch --merged | egrep -v "\*|${PROTECT_BRANCHES}" | xargs git branch -d
    else
        echo
        echo "bye!"
    fi
}

# create repository by github cli
gh-create-repository() {
    if [ -z "$1" ]; then
        echo "please specify repository"
        exit 1
    else
        :
    fi

    echo $@
    gh repo create $@
    ghq get $1
    code $(ghq list --full-path -e $1)

}

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

#######################
#  enable fzf   #
#######################
# C-r: cmd history
# C-t: explor child directory
source ~/.fzf/shell/key-bindings.zsh

#####################
# ALIASES           #
#####################
# * alias
alias vi='/usr/bin/vim'

alias tree='exa --tree --icons --classify --group'
alias ls='exa --classify --group-directories-first --icons --group'
alias la='exa --classify --group-directories-first --icons -a'
alias ll='exa --classify --group-directories-first --icons -l'
alias lla='exa --classify --group-directories-first --icons -la'

alias bd='cd ..' # * need enhancd

alias hc='fzf-history-widget'

alias k='kubectl'
alias kc='kubectx'
alias kn='kubens'

alias g='git'
alias gb='git branch'
alias gpl='git pull'
alias gps='git push'
alias gco='git checkout'
alias gbd='cd-gitroot'
alias gcd='cd $(ghq root)/$(ghq list | fzf)'
alias gcode='${OPEN_BY_MY_EDITOR} $(ghq root)/$(ghq list | fzf)'


alias d='docker'
alias dc='docker-compose'

alias ff='fzf'

alias ghq-rm='ghq-rm.sh'
alias ggrks='open'
alias ghcr='gh-create-repository'
alias gmail='open "https://mail.google.com/mail/u/0/#inbox"'

##################
# set completion #
##################
# NOTE: add fpath and source -> compdef -> compinit
fpath=(~/.zsh/completion $fpath)

eval "$(gh completion -s zsh)"
# this is native kubectl completion, but poor (e.g. does not complete flag, have not explain)
# however, fast
# source <(kubectl completion zsh)

# load compinit func (func is not automatically loaded)
autoload -Uz compinit
compinit

