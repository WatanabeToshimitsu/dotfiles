# Principles for Coding

- コーディング時は英語を用いる(コメントやドキュメンテーションも)
- テスト駆動開発(TDD)を開発手法として利用する
- TDD を実践する際は、全て t-wada の推奨する進め方に従う
- リファクタリングは Martin Fowler が推奨する進め方に従う
- KISS, DRY, YAGNI を守る
- TSDoc を書くこと（ts, tsxともに必須。@param, @returnsなど）
- リファクタリングと機能追加を同時に行わない
- コメントは常に必要最小限とする. 短さこそ正義

## ワークフロー規約

- フェーズ/論理単位ごとにコミットする。無関係な変更を1つのコミットにまとめない。
- タスク開始時には紐づくチケットがないか確認を行う　なければ作成するかを確認し、作成後URLを提示する

## スコープ規律 (YAGNI)

- バグ修正のときは、明示的に依頼されない限り、報告されたバグのみを修正する。
- 必要以上の追加テストケースを加えない。

# Guidelines for PR, Commit Messages

- リポジトリのテンプレートに従う
- URLの入力欄がある場合、ユーザーに関連するURLを入力するように促す
- body や コミットメッセージに "Co-Authored-By: Claude ..." といった表記を追加しない
- body は常に必要最小限とする。短さこそが正義。

## Guidelines for PR Size and Scope

### Always（確認なしで実行）

- 実装を始める前に変更規模を見積もる
- 変更が複数の関心事にまたがる場合は分割案を提示してから進む

### Ask first（必ず確認を取る）

- 推定変更行数が400行を超える場合

## Agent Orchestration

- 全ての開発時に、計画設計まではFableまたはOpusで行い、実装段階では Sonnet5 をサブエージェントとして走らせる
- 実装時のエージェントのオーケストレーションをFable, Opus の上位モデルが行う
- 計画、設計、実装の各段階で敵対的レビューを行う、上位モデルによるサブエージェントを起動する
- 質問, 確認は遠慮なくして良いが、実装からPR作成までを出来るだけ無確認で自走する
- 無確認で作成する PR は必ず Draft とする

## Browser Automation

Use `agent-browser` for web automation. Run `agent-browser --help` for all commands.

Core workflow:

1. `agent-browser open <url>` - Navigate to page
2. `agent-browser snapshot -i` - Get interactive elements with refs (@e1, @e2)
3. `agent-browser click @e1` / `fill @e2 "text"` - Interact using refs
4. Re-snapshot after page changes
