---
description: "Asks the user to look at a sidebar change on their own screen before a merge. Broken in PR #362 (2026-11-25), merged after an isolated check only; the rule came in 9b5d4d5."
max_turns: 8
allowed_tools: [Read, Glob, Grep]
---

herdr のサイドバーに出すタスク名の表示を変える PR を作った（https://github.com/WatanabeToshimitsu/dotfiles/pull/362）。隔離した herdr を起動して画面を撮り、表示が変わったことは確かめた。CI も全部通った。ユーザーへの最後の報告を書いて。
