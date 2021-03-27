ZSH_GIT_PROMPT_FORCE_BLANK=0
ZSH_GIT_PROMPT_SHOW_UPSTREAM="full"

ZSH_THEME_GIT_PROMPT_PREFIX=""
ZSH_THEME_GIT_PROMPT_SUFFIX=""
ZSH_THEME_GIT_PROMPT_SEPARATOR=" | "
ZSH_THEME_GIT_PROMPT_DETACHED="%{$fg_bold[cyan]%}: "
ZSH_THEME_GIT_PROMPT_BRANCH="%{$fg_bold[cyan]%} "
ZSH_THEME_GIT_PROMPT_UPSTREAM_SYMBOL="%{$fg_bold[green]%}⟳ "
ZSH_THEME_GIT_PROMPT_UPSTREAM_PREFIX="%{$fg[black]%}(%{$fg[black]%}"
ZSH_THEME_GIT_PROMPT_UPSTREAM_SUFFIX="%{$fg[black]%})"
ZSH_THEME_GIT_PROMPT_BEHIND="↓ "
ZSH_THEME_GIT_PROMPT_AHEAD="↑ "
ZSH_THEME_GIT_PROMPT_UNMERGED="%{$fg[red]%}UNMERGE✖ "
ZSH_THEME_GIT_PROMPT_STAGED="%{$fg[blue]%}● "
ZSH_THEME_GIT_PROMPT_UNSTAGED="%{$fg[yellow]%}✚ "
ZSH_THEME_GIT_PROMPT_UNTRACKED="%{$fg[black]%}…"
ZSH_THEME_GIT_PROMPT_STASHED="%{$fg[red]%}STASH⚑ "
ZSH_THEME_GIT_PROMPT_CLEAN="%{$fg_bold[green]%}✔ "

# In the second line of the prompt $psvar[12] is read
PROMPT=$'%~ %F{242}$(gitprompt)%f
%(12V.%F{242}%12v%f .)> '

# right side is kube status
# KUBE_PS1_BINARY=kubectl
# KUBE_PS1_NS_ENABLE=true
KUBE_PS1_PREFIX=""
KUBE_PS1_SYMBOL_ENABLE=""
KUBE_PS1_SYMBOL_DEFAULT=""
KUBE_PS1_SYMBOL_USE_IMG=true
KUBE_PS1_SEPARATOR=''
KUBE_PS1_DIVIDER="."
KUBE_PS1_SUFFIX=""

KUBE_PS1_SYMBOL_COLOR='white'
KUBE_PS1_CTX_COLOR='cyan'
KUBE_PS1_NS_COLOR='cyan'
KUBE_PS1_BG_COLOR=''
source /usr/local/bin/kube-ps1/kube-ps1.sh
RPROMPT='$(kube_ps1)'


setup() {
    [[ -n $_PROMPT_INITIALIZED ]] && return
    _PROMPT_INITIALIZED=1

    # Prevent Python virtualenv from modifying the prompt
    export VIRTUAL_ENV_DISABLE_PROMPT=1

    # Set $psvar[12] to the current Python virtualenv
    function _prompt_update_venv() {
        psvar[12]=
        if [[ -n $VIRTUAL_ENV ]] && [[ -n $VIRTUAL_ENV_DISABLE_PROMPT ]]; then
            psvar[12]="${VIRTUAL_ENV:t}"
        fi
    }
    add-zsh-hook precmd _prompt_update_venv

    # Draw a newline between every prompt
    function _prompt_newline(){
        if [[ -z "$_PROMPT_NEWLINE" ]]; then
            _PROMPT_NEWLINE=1
        elif [[ -n "$_PROMPT_NEWLINE" ]]; then
            echo
        fi
    }
    add-zsh-hook precmd _prompt_newline

    # To avoid glitching with fzf's alt+c binding we override the fzf-redraw-prompt widget.
    # The widget by default reruns all precmd hooks, which prints the newline again.
    # We therefore run all precmd hooks except _prompt_newline.
    function fzf-redraw-prompt() {
        local precmd
        for precmd in ${precmd_functions:#_prompt_newline}; do
            $precmd
        done
        zle reset-prompt
    }
}
setup
