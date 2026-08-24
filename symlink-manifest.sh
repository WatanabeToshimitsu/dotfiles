# Shared manifest of dotfiles symlinked by install.sh and removed by uninstall.sh.
# Sourced only — keep in sync with the actual repo layout.

# shellcheck disable=SC2034  # consumed by install.sh / uninstall.sh via source
MANIFEST_FILES=(
  .zshrc .bashrc .bash_profile .bash_logout
  .profile .zprofile .zshenv .shell-common
  .vimrc .tmux.conf .gitconfig
  .huskyrc .npmrc
)

# .config/ subdirectory files
# shellcheck disable=SC2034  # consumed by install.sh / uninstall.sh via source
MANIFEST_CONFIG_FILES=(
  .config/git/ignore
  .config/gh/config.yml
  .config/ghostty/config
  .config/herdr/config.toml
  .config/yazi/yazi.toml
)

# Claude Code global settings (claude/ → ~/.claude/)
# shellcheck disable=SC2034  # consumed by install.sh / uninstall.sh via source
MANIFEST_CLAUDE_FILES=(
  CLAUDE.md
  RTK.md
  settings.json
  statusline.sh
  claude-powerline.json
  hooks/deny-check.sh
  hooks/link-worktree-memory.sh
  hooks/notification.sh
  hooks/post-ts-lint.sh
  hooks/require-subagent-model.sh
  hooks/rtk-rewrite.sh
  hooks/validate-bash.sh
  rules/common/agents.md
  rules/common/code-review.md
  rules/common/coding-style.md
  rules/common/development-workflow.md
  rules/common/git-workflow.md
  rules/common/hooks.md
  rules/common/patterns.md
  rules/common/performance.md
  rules/common/security.md
  rules/common/testing.md
  rules/golang/coding-style.md
  rules/golang/hooks.md
  rules/golang/patterns.md
  rules/golang/security.md
  rules/golang/testing.md
  rules/python/coding-style.md
  rules/python/fastapi.md
  rules/python/hooks.md
  rules/python/patterns.md
  rules/python/security.md
  rules/python/testing.md
  rules/testing/vitest.md
  rules/typescript/coding-style.md
  rules/typescript/documentation.md
  rules/typescript/hooks.md
  rules/typescript/patterns.md
  rules/typescript/security.md
  rules/typescript/testing.md
  rules/typescript/type-safety.md
)
