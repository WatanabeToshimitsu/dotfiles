# Principles for Coding

- コーディング時は英語を用いる(コメントやドキュメンテーションも英語)
- テスト駆動開発(TDD)を開発手法として利用する
- TDD を実践する際は、全て t-wada の推奨する進め方に従う
- リファクタリングは Martin Fowler が推奨する進め方に従う
- KISS, DRY, YAGNI を守る
- TSDoc を書くこと（ts, tsxともに必須。@param, @returnsなど）
- すべての .ts / .tsx ファイルの冒頭に、そのファイルの役割・責務を2行程度で記述
- コロケーションを重視する
- UIは視線の流れを意識する

# Guidelines for Code Review

3つの code-review 系プラグインが共存しているため、用途で呼び分ける。

- **日常のローカル diff レビュー**: `/code-review:review`（公式・confidence ≥80 のバグだけ報告）
- **PR 提出前の総合チェック**: `/review-pr`（pr-review-toolkit・6専門agentで網羅）
- **社内 (HDL) 規約レビュー**: `/hdl-review`（backend/frontend/ml 別の社内ルールを適用）
- **修正ループ**: `/review-fix-loop`（指摘の反映と検証を自動で回す）

迷ったらまず `/hdl-review` を使う。長期的には公式 `pr-review-toolkit` への統合を目指す。

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
- 数行にも及ぶコメントは推奨されない。数行のコメントが必要な場合、コードをリファクタリングし、コメントなしで理解できるようにする
- ドキュメンテーションは、ユーザーがコードを理解しやすくするための情報を提供するために記述する。コードの実装の詳細を説明するために使用しないこと。
