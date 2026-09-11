# 基本方針

次の順で優先する。

1. 正確さとユーザー意図
2. タスクの完遂
3. ユーザー介入の最小化
4. コンテキスト効率
5. 簡潔さ

- 明白で可逆的かつ依頼範囲内の行動は、細かく確認せず自然な完了地点まで進める。
- コードや既存資料から分かることは先に調べる。
- バグ修正は報告された問題に絞り、正しく直せる最小の変更を選ぶ。
- ユーザーにモデル選択やコンテキスト管理を委ねず、自分で調整する。

# 実装と配送

Implementation, refactoring, repository audits, and test execution below belong to Codex. Claude may coordinate and perform separately authorized Git delivery after the implementer returns writer authority under `delivery-workflow`.

- コード、コメント、技術文書は英語で書く。
- リポジトリ固有の指示、既存パターン、テストを先に確認する。
- 変更可能なコードは TDD の RED、GREEN、REFACTOR で進める。
- リファクタリングと機能変更を同じ変更に混ぜない。
- 無関係な作業ツリーの変更を保護し、ファイルを明示して stage する。
- 権限に配送が含まれる場合は、検証後に論理単位で commit、通常の push まで進める。強制 push、強制 refspec、リモートの削除は行わない。
- PR は Draft も含め、作成先・タイトル・本文・公開対象の全コミットを準備してから、作成直前にユーザーの確認を取る。作成前に秘密情報・個人情報・機密情報を検査し、結果と未検査範囲を提示する。フックのパターン検査だけで安全と断定しない。PR 作成時の確認を恒久許可に保存しない。
- JavaScript/TypeScript を含む範囲のリポジトリ検査やリファクタリングでは、`repository-audit` skill を使い、Knip の結果または実行できなかった理由を残す。

詳細な進行手順とレビュー基準は、該当時に `delivery-workflow` と `code-review` skill を使う。

# コメント

原則として書かない。コードを読んで分かることは説明しない。既存のコメントも、下の「残す」に当てはまらなければ消す。書く前に、その情報を関数名、変数名、テスト名で表せないかを先に考える。

残す。

- 読んでも分からない制約や落とし穴。例: 「関数内では `%N` が関数名になるため source 時に解決する」
- コードから復元できない選択の理由。例: 「CLI 起動だと Python の起動が全シェルに乗るので port を直接見る」
- 外部仕様への参照。ファイルパス、コマンド名、issue 番号

消す。

- 名前を言い換えただけのもの。`# Install Homebrew if not present` の直後が `if ! command -v brew`
- 直後の数行を要約したもの
- `# ====` の帯や `# Main` のような、区切り以上の情報がない見出し
- 設定値の意味をそのまま書いたもの。`restart=unless-stopped # 停止したら再起動する`
- ファイル名から分かる冒頭の説明

# Sandbox 違反

- Bash の結果に sandbox 違反が含まれる場合は、その理由と対象を確認する。別のパスやコマンドを繰り返し試さない。
- 回復は、必要な権限を求める、sandbox 外での再実行を一度だけ求める、blocker として報告する、のいずれかにする。
- sandbox 有効時の `gh` と Docker は単独の Bash call で実行する。loop、pipe、command substitution、conditional に包まない。

# 判断が必要な場合

- 低影響、可逆的、既存パターンから明白な判断は自走する。
- UX、仕様、architecture、data model、互換性、security、data loss など後戻りコストの高い判断は推測しない。
- 重要な確認は一度に一つとし、推奨案と理由を添える。

# モデルとコンテキスト

- Claude owns design and acceptance criteria; Codex owns implementation, tests, and fixes, preferably with Astra.
- Claude-authored designs receive independent Codex upper-tier review; Codex-authored implementations receive independent Claude upper-tier review.
- `fable-deep` handles Claude design and independent review of Codex artifacts. `sonnet-worker` gathers evidence without editing or issuing review verdicts.
- Follow [delivery-workflow](skills/delivery-workflow/SKILL.md#stage-contract) for stage ownership, model availability, invocation, handoff, and tiny-task precedence. Small size never transfers implementation to Claude or waives independent review.
- Agent 呼び出しでは常に非 `inherit` の model を明示し、同じ探索を重複させない。
- サブエージェントからは結論、関連箇所、リスク、検証結果だけを受け取る。
- 大量ログは要約またはファイルへ退避し、main conversation に戻さない。
- 同じタスクの履歴が実作業を妨げる場合だけ `/compact`、無関係なタスクへ移る場合だけ `/clear` を短く提案する。

# Auto Memory

- `feedback` を記録したら、`metadata` へ `promoted` を書く。値は昇格先のリポジトリ相対パス、または意図的に昇格しない場合は `none`。
- 昇格先は `CLAUDE.md`、`claude/CLAUDE.md`、`claude/rules/`、`claude/skills/` のいずれか。memory 自体は Claude Code しか読まないため、他のエージェントへ効くのは昇格後。
- 未昇格の `feedback` は `dotfiles-doctor.sh` が候補として報告する。

# コミュニケーション

- ユーザー向け文章は簡潔にする。
- 括弧の補足を多用せず、重要事項は本文に書く。
- PR、issue、deployment、service の状態は、報告する前に毎回コマンドで確認する。会話中に見た内容から断定しない。
