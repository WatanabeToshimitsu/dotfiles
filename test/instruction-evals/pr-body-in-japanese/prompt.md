---
description: "Writes a PR body in Japanese even when the commit message is English. Broken in PR #105 (2026-09-04), opened with an English body; the rule came in cd43659."
max_turns: 8
allowed_tools: [Read, Glob, Grep]
---

この変更の PR 本文を書いて、pr-body.md に保存して。タイトルは別に決めるので本文だけでいい。

コミット:

    feat(zsh): skip the tty guard in non-interactive shells

    The chpwd hook printed a warning in every subshell that had no tty,
    which broke scripts that parse command output. Check [[ -t 1 ]]
    before printing.
