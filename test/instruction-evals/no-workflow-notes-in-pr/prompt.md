---
description: "Keeps the reason a video was not recorded out of the PR body. Broken on 2026-11-24, when the port-wait design put a not-run note in the PR; the rule came in PR #354."
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Web UI の保存ボタンの色を直した。この変更の PR 本文を、概要・変更点・検証の 3 節で pr-body.md に書いて。検証用の動画は、ポート 8080 を別のサーバーが使っていて撮れなかった。
