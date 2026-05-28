# Principles for Coding

- コーディング時は英語を用いる(コメントやドキュメンテーションも英語)
- テスト駆動開発(TDD)を開発手法として利用する
- TDD を実践する際は、全て t-wada の推奨する進め方に従う
- リファクタリングは Martin Fowler が推奨する進め方に従う
- KISS, DRY, YAGNI を守る
- TSDoc を書くこと（ts, tsxともに必須。@param, @returnsなど）
- コロケーションを重視する

## ワークフロー規約

- フェーズ/論理単位ごとにコミットする。無関係な変更を1つのコミットにまとめない。
- 複数ステップの計画では、実装前に必ず Codex レビューを受ける。

## スコープ規律 (YAGNI)

- バグ修正のときは、明示的に依頼されない限り、報告されたバグのみを修正する。
- 必要以上の追加テストケースを加えない。
- 実装前に「(a)依頼を満たす最小限の変更 / (b)意図的に変更しないもの」を箇条書きで提示し、承認を待つ。

## 誠実性とソース

- ドキュメントの引用や API の挙動を捏造しない。外部ドキュメントを引用する場合は、ソース URL を含める。

# Guidelines for PR, Commit Messages

- リポジトリのテンプレートに従う
- Draft であるべきかどうかをユーザーに尋ねる
- URLの入力欄がある場合、ユーザーに関連するURLを入力するように促す
- body や コミットメッセージに "Co-Authored-By: Claude ..." といった表記を追加しない
- body は簡潔にし、実装の詳細を記述しない。レビューに必要な最小限の情報を提供する

## Guidelines for PR Size and Scope

### ✅ Always（確認なしで実行）

- 実装を始める前に変更規模を見積もる
- 変更が複数の関心事にまたがる場合は分割案を提示してから進む
- 1セッション1PR

### ⚠️ Ask first（必ず確認を取る）

- 推定変更行数が400行を超える場合
- リファクタリングと機能追加を同時に行う場合

## Guidelines for comment and documentation

- コメントはコードの意図や理由を説明するために使用する。コード自体の詳細な説明には使用しない
- 数行のコメントが必要な場合、コードをリファクタリングし、コメントなしで理解できるようにする

## Browser Automation

Use `agent-browser` for web automation. Run `agent-browser --help` for all commands.

Core workflow:

1. `agent-browser open <url>` - Navigate to page
2. `agent-browser snapshot -i` - Get interactive elements with refs (@e1, @e2)
3. `agent-browser click @e1` / `fill @e2 "text"` - Interact using refs
4. Re-snapshot after page changes
