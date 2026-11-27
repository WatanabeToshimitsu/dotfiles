---
description: "Writes an issue body in Japanese even when the evidence is English. The rule covers PR and issue bodies and was broken in PR #105 (2026-09-04), opened with an English body; it came in cd43659. The PR route now also gets Japanese from delivery-workflow's verification line, so this case uses an issue body."
max_turns: 8
allowed_tools: [Read, Glob, Grep]
---

この不具合の issue を立てたいので、本文を issue-body.md に書いて。タイトルは別に決める。

    $ zsh -c 'cd /tmp && git status --porcelain' | wc -l
    warning: chpwd hook: no tty attached
          1

非対話のシェルでも chpwd hook が警告を出していて、出力を数えるスクリプトが壊れる。
