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
# git prune
git-branch-prune() {
    PROTECT_BRANCHES='master|develop|trunk|main|staging|production|release'

    if [ -z "$1" ]; then
        :
    else
        PROTECT_BRANCHES="${PROTECT_BRANCHES}|$1"
    fi

    echo "fetching..."
    git fetch --prune

    # メインブランチを特定（origin/プレフィックス付きで取得）
    MAIN_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/@@')
    if [ -z "$MAIN_BRANCH" ]; then
        # HEAD が設定されていない場合は候補から検索（ローカルまたはリモート）
        for branch in trunk main master; do
            if git show-ref --verify --quiet refs/heads/$branch; then
                MAIN_BRANCH=$branch
                break
            elif git show-ref --verify --quiet refs/remotes/origin/$branch; then
                MAIN_BRANCH="origin/$branch"
                break
            fi
        done
    fi

    if [ -z "$MAIN_BRANCH" ]; then
        echo "Error: Could not determine main branch"
        return 1
    fi

    echo "Using main branch: $MAIN_BRANCH"

    # 1. 従来の方法: git branch --merged で検出（メインブランチに対して）
    echo
    echo "=== Checking merged branches (traditional merge) ==="
    MERGED_BRANCHES=""
    git branch --merged "$MAIN_BRANCH" 2>/dev/null | while read branch; do
        branch=$(echo "$branch" | sed 's/^[[:space:]]*\*[[:space:]]*//' | sed 's/^[[:space:]]*//')
        if [ -n "$branch" ]; then
            # 保護ブランチかチェック
            is_protected=0
            for protected in master develop trunk main staging production release; do
                if [ "$branch" = "$protected" ]; then
                    is_protected=1
                    break
                fi
            done
            if [ $is_protected -eq 0 ]; then
                MERGED_BRANCHES="${MERGED_BRANCHES}${branch}"$'\n'
            fi
        fi
    done
    echo "Found $(echo "$MERGED_BRANCHES" | sed '/^$/d' | wc -l | tr -d ' ') branches"

    # 2. GitHub CLI: マージ済みPRからブランチを検出
    echo "=== Checking merged PRs (including squash merge) ==="
    MERGED_PR_BRANCHES=""
    if command -v gh &> /dev/null; then
        gh pr list --state merged --limit 1000 --json headRefName --jq '.[].headRefName' 2>/dev/null | while read branch; do
            if [ -z "$branch" ]; then
                continue
            fi
            # ローカルブランチとして存在するかチェック
            if git show-ref --verify --quiet refs/heads/"$branch"; then
                # 保護ブランチかチェック
                is_protected=0
                for protected in master develop trunk main staging production release; do
                    if [ "$branch" = "$protected" ]; then
                        is_protected=1
                        break
                    fi
                done
                if [ $is_protected -eq 0 ]; then
                    MERGED_PR_BRANCHES="${MERGED_PR_BRANCHES}${branch}"$'\n'
                fi
            fi
        done
        echo "Found $(echo "$MERGED_PR_BRANCHES" | sed '/^$/d' | wc -l | tr -d ' ') branches from merged PRs"
    else
        echo "Warning: gh command not found. Squash-merged branches may not be detected."
    fi

    # 3. 両方の結果を統合（重複排除）
    DELETE_BRANCHES=$(echo -e "${MERGED_BRANCHES}\n${MERGED_PR_BRANCHES}" | sort -u | sed '/^$/d')

    # 4. 現在進行中のブランチ（remained branches）を取得
    REMAINED_BRANCHES=""
    ALL_BRANCHES=$(git branch 2>/dev/null | sed 's/^[[:space:]]*\*[[:space:]]*//' | sed 's/^[[:space:]]*//')
    for branch in ${(f)ALL_BRANCHES}; do
        if [ -z "$branch" ]; then
            continue
        fi
        # 保護ブランチかチェック
        is_protected=0
        for protected in master develop trunk main staging production release; do
            if [ "$branch" = "$protected" ]; then
                is_protected=1
                break
            fi
        done
        # 削除対象かチェック
        is_to_delete=0
        for del_branch in ${(f)DELETE_BRANCHES}; do
            if [ "$branch" = "$del_branch" ]; then
                is_to_delete=1
                break
            fi
        done
        if [ $is_protected -eq 0 ] && [ $is_to_delete -eq 0 ]; then
            REMAINED_BRANCHES="${REMAINED_BRANCHES}${branch}"$'\n'
        fi
    done

    # 表示
    echo
    echo "=== Branches to be deleted ($(echo "$DELETE_BRANCHES" | sed '/^$/d' | wc -l | tr -d ' ') total) ==="
    if [ -n "$DELETE_BRANCHES" ]; then
        echo "$DELETE_BRANCHES"
    else
        echo "(none)"
    fi

    echo
    echo "=== Protected branches ==="
    git branch 2>/dev/null | while read branch; do
        branch=$(echo "$branch" | sed 's/^[[:space:]]*\*[[:space:]]*//' | sed 's/^[[:space:]]*//')
        for protected in master develop trunk main staging production release; do
            if [ "$branch" = "$protected" ]; then
                current_marker=""
                git branch | command grep "^\* $branch" > /dev/null 2>&1 && current_marker="* "
                echo "${current_marker}${branch}"
                break
            fi
        done
    done

    echo
    echo "=== Remained branches (in progress, $(echo "$REMAINED_BRANCHES" | sed '/^$/d' | wc -l | tr -d ' ') total) ==="
    if [ -n "$REMAINED_BRANCHES" ] && [ "$(echo "$REMAINED_BRANCHES" | sed '/^$/d' | wc -l)" -gt 0 ]; then
        echo "$REMAINED_BRANCHES" | sed '/^$/d'
    else
        echo "(none)"
    fi

    if [ -z "$DELETE_BRANCHES" ]; then
        echo
        echo "No branches to delete."
        return 0
    fi

    echo
    echo "Delete these branches? (y/N): "

    if read -q; then
        echo
        echo "Deleting..."
        FAILED_BRANCHES=()
        for branch in ${(f)DELETE_BRANCHES}; do
            if [ -z "$branch" ]; then
                continue
            fi

            # PR検出ブランチかチェック（スカッシュマージ対応）
            is_pr_branch=0
            for pr_branch in ${(f)MERGED_PR_BRANCHES}; do
                if [ "$branch" = "$pr_branch" ]; then
                    is_pr_branch=1
                    break
                fi
            done

            if [ $is_pr_branch -eq 1 ]; then
                # GitHub PR経由で検出されたブランチは強制削除（スカッシュマージ済み）
                if git branch -D "$branch" 2>/dev/null; then
                    echo "✓ Deleted (force): $branch"
                else
                    echo "✗ Failed to delete: $branch"
                    echo "  Reason: $(git branch -D "$branch" 2>&1)"
                    FAILED_BRANCHES+=("$branch")
                fi
            else
                # 通常マージ検出のブランチは安全な削除
                if git branch -d "$branch" 2>/dev/null; then
                    echo "✓ Deleted: $branch"
                else
                    echo "✗ Failed to delete: $branch"
                    echo "  Reason: $(git branch -d "$branch" 2>&1)"
                    FAILED_BRANCHES+=("$branch")
                fi
            fi
        done

        if [ ${#FAILED_BRANCHES[@]} -gt 0 ]; then
            echo
            echo "Some branches could not be deleted. You can manually delete them with:"
            for branch in "${FAILED_BRANCHES[@]}"; do
                echo "  git branch -D $branch"
            done
        fi

        echo "Done!"
    else
        echo
        echo "Cancelled."
    fi
}

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

# oh-my-posh prompt theming
command -v oh-my-posh &>/dev/null && eval "$(oh-my-posh init zsh --config ~/oh-my-posh-theme/myconfig.omp.json)"

# Claude experimental agent teams feature
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
[[ -f ~/.safe-chain/scripts/init-posix.sh ]] && source ~/.safe-chain/scripts/init-posix.sh
