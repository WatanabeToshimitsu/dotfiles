# エージェント運用ガイド

Claude Code・Codexの状態確認と、使い方を調整するときの手順です。環境全体の構成と導入方法は[README](../README.md)を参照してください。

## 目次

- [エージェント環境の診断](#agent-diagnostics)
- [Claudeのツール出力の圧縮](#claude-tool-output-compaction)
- [Headroomによる応答量の調整](#headroom-proxy)
- [ClaudeのBash sandbox](#claude-bash-sandbox-canary)
- [Auto Memoryと共通ルールへの反映](#claude-auto-memory)
- [定期実行をエージェントに依頼する](#loop-contracts)

<a id="agent-diagnostics"></a>

## エージェント環境の診断

以下のコマンドで、エージェント環境をまとめて確認できます。

```bash
~/.shell-utils/dotfiles-doctor.sh --harness-only
```

現在の診断対象は、Headroomへの接続と削減量、MCP接続、Claude Codeのバージョン差分、Codex設定の同期状態です。出力圧縮フックの動作確認は診断対象外のため、圧縮量は[専用の統計コマンド](#claude-tool-output-compaction)で確認できます。

オプションを付けずに実行すると、端末の設定とリポジトリの差分や、Auto Memoryから共通ルールへの反映待ちも確認できます。

```bash
~/.shell-utils/dotfiles-doctor.sh
```

macOSでは、`install.sh`が毎週月曜10:00の診断を登録します。以下のコマンドで、登録状態と直近の診断結果を確認できます。

```bash
launchctl print "gui/$(id -u)/com.kz86n.dotfiles-doctor"
tail -n 80 ~/Library/Logs/dotfiles-doctor.log
```

`last exit code`が`0`なら警告なし、`1`なら警告があります。詳しい内容はログを確認してください。

<a id="claude-tool-output-compaction"></a>

## Claudeのツール出力の圧縮

大きなRead・Grep・Glob・Web・MCPの結果は、フックによって会話に入る前に短縮されます。全文はローカルに7日間保存されます。省略された内容が必要なときは、エージェントに[`expand-tool-output`](../claude/skills/expand-tool-output/SKILL.md)での再取得を依頼してください。

以下のコマンドで、保存中のアーカイブから出力の削減量を確認できます。

```bash
python3 ~/.claude/hooks/compact-tool-output.py stats
```

<a id="headroom-proxy"></a>

## Headroomによる応答量の調整

`install.sh`では、Headroomを導入し、Claude Code・Codexの通信をローカルプロキシへ通す設定を行います。応答の長さを調整する構成になっており、macOSではlaunchdがログイン時の起動と異常終了時の再起動を担います。

会話の10%は調整をかけず、削減効果を測るための比較対象になります。`headroom output-savings`の`MEASURED`は比較対象を使った実測、`ESTIMATED`は合成した基準値による推定です。

以下のコマンドで、プロキシの状態と出力の削減量を調べることができます。

```bash
headroom install status
headroom doctor
headroom output-savings
```

Claudeの履歴がたまったら、以下のコマンドで好みの応答の長さを学習し直せます。

```bash
headroom learn --verbosity --apply --all
```

<a id="claude-bash-sandbox-canary"></a>

## ClaudeのBash sandbox

通常の`claude`は、操作の許可判定を自動化するAutoモードで動きます。ファイルやネットワークへのアクセスをOS側でも制限したい場合は、macOS向けの試行環境`claude-sandbox`を利用できます。

以下のコマンドで、設定の確認とsandbox付きの起動ができます。

```bash
claude-sandbox --check
claude-sandbox
```

使えるコマンドや通信先に制限があるため、利用前に[Sandbox Canaryの対象範囲と制約](../claude/SANDBOX.md)を確認してください。

<a id="claude-auto-memory"></a>

## Auto Memoryと共通ルールへの反映

記憶の保存にはClaude Code標準のAuto Memoryを使っており、同じリポジトリのworktree間で共有されます。

このリポジトリ独自の仕組みは、学びを共通ルールに反映したかどうかの管理です。エージェントはfeedback形式の記憶に`metadata.promoted`を記録し、`CLAUDE.md`・ルール・スキルへの反映先、または反映しない判断を残します。doctorはこの情報から反映待ちを報告します。

今後も守ってほしい好みや方針は、エージェントに伝えてください。[`claude/AUTO-MEMORY.md`](../claude/AUTO-MEMORY.md)は、この独自の管理方法を説明する資料です。

<a id="loop-contracts"></a>

## 定期実行をエージェントに依頼する

定期実行を頼むときは、任せたい作業、触れてよい範囲、時間・回数の上限、判断に迷ったら確認してほしい点を伝えてください。実行方法や検証コマンドはエージェントが調べ、承認用の実行案にまとめます。

実行案は「Loop契約」と呼びます。内容を確認して承認すると、その範囲で定期実行を設定できます。契約が未承認の間は、リポジトリの変更を許可しない構成です。具体的な準備・実行手順は、エージェント向けの[`delivery-workflow`](../claude/skills/delivery-workflow/SKILL.md#scheduled-repository-work)にまとめています。

dotfilesでは試行・検証段階です。[2026年9月9日の試行記録](https://github.com/WatanabeToshimitsu/dotfiles/issues/60#issuecomment-5596708889)では、定期タスクが2回起動し、1回は追加の許可待ちで停止、1回は読み取り専用の調査を完了しました。受け入れ条件は未達で常設化は見送られています。1件の変更を任せる試行も未着手です。進捗は[読み取り専用の試行 #60](https://github.com/WatanabeToshimitsu/dotfiles/issues/60)と[変更作業の試行 #61](https://github.com/WatanabeToshimitsu/dotfiles/issues/61)で管理しています。
