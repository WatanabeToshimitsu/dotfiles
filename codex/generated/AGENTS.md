# 基本方針

次の順で優先する。

1. 正確さとユーザー意図
2. タスクの完遂
3. ユーザー介入の最小化
4. コンテキスト効率
5. 簡潔さ

- 明白で可逆的かつ依頼範囲内の行動は、細かく確認せず自然な完了地点まで進める。
- コードや既存資料から分かることは先に調べる。
- 他リポジトリを参照する調査や実装では、先に origin を fetch し、origin の既定ブランチ（trunk / main）の内容を根拠にする。作業ブランチや古いローカル checkout を根拠にしない。
- バグ修正は報告された問題に絞り、正しく直せる最小の変更を選ぶ。
- ユーザーにモデル選択やコンテキスト管理を委ねず、自分で調整する。
- For widespread test or CI failures, group them and seek a shared cause first, from recent changes out to dependencies, mocks, setup, or runtime; keep confirmed causes apart from hypotheses, and narrow the search if none is found.
- For an open architecture or infrastructure choice, table two or three viable options before exploring one deeply, including a simpler managed one or why it is unsuitable, and recommend one by requirements and trade-offs; skip small changes, obvious fixes, and settled user choices.

# 実装と配送

- コード、コメント、技術文書は英語で書く。
- 変更可能なコードは TDD の RED、GREEN、REFACTOR で進める。
- Give `git push` a literal absolute repo path, such as `rtk proxy git -C /absolute/repo push origin topic`, even when `workdir` is set; Codex shell hooks may see only the command and session cwd.
- For Codex CLI PR creation, use an absolute `--body-file` path.
- Before every PR, including a Draft, follow `delivery-workflow` step 8. In Codex, also finish inspection and get explicit user authorization before a PR tool call, as hook warnings cannot pause it.
- Run long-lived Node processes such as dev servers, watchers, and Storybook with `memgate run -- <command>`; `agent-browser` already does. If memgate refuses for memory, stop idle servers and browsers you started and retry; never bypass it.
- Before opening a web app with agent-browser, follow the [browser login rule](rules/web/browser-login.md); it also limits production use.
- Call 1Password's `op` by its bare name, not a path or script, so the Claude Code permission prompt shows each call. Pass secrets straight to their consumer with a pipe, `$(op read ...)`, `op run` without `--no-masking`, or `op inject -o <file>`, keep them out of output and logs, and check the command does not echo them.
- JavaScript/TypeScript を含む範囲のリポジトリ検査やリファクタリングでは、`repository-audit` skill を使い、Knip の結果または実行できなかった理由を残す。

詳細な手順とレビュー基準は `delivery-workflow` と `code-review` skill に従う。

# 長い作業と goal

Read the [goal guidance](skills/delivery-workflow/references/goals.md) near the start, or once the size becomes clear, for work likely to span multiple PRs, need substantial investigation, take about an hour or more, or need staged planning; also for goal requests and feedback on a pending plan handoff, even in a later chat. Re-read it on goal activation and completion, before drafting goals or plan updates, and after compaction mid-goal.
If it is unreadable, say so, stop dependent goal drafting and handoffs, continue independent authorized work, and never rebuild its rules from memory.

# Claude Code Configuration Scope

- Default Claude Code skills, commands, settings, hooks, and permission rules to
  user scope unless the user explicitly requests project or local scope.
  In dotfiles, keep managed sources under `claude/` for the existing installation
  flow to distribute to `~/.claude/`.
- Before proposing an allowlist entry, read the effective user/project/local
  permission rules in `~/.claude/settings.json`, `.claude/settings.json`, and
  `.claude/settings.local.json` or `/permissions`. Do not add an entry already
  covered by an existing wildcard.
- Scope determines placement. Follow the request and existing approval procedures
  when editing permissions or applying changes to the user profile.

# コメント

コードには How、テストコードには What、コミットログには Why、コードコメントには Why not を書く。Why not は、別の書き方を採らなかった理由を指す。ルールやツールが求めるものを除き、それ以外のコードコメントは書かない。

# Sandbox 違反

- Bash の結果に sandbox 違反が含まれる場合は、その理由と対象を確認する。別のパスやコマンドを繰り返し試さない。
- 回復は、必要な権限を求める、sandbox 外での再実行を一度だけ求める、blocker として報告する、のいずれかにする。
- sandbox 有効時の `gh` と Docker は単独の Bash call で実行する。loop、pipe、command substitution、conditional に包まない。

# 判断が必要な場合

- 低影響、可逆的、既存パターンから明白な判断は自走する。
- UX、仕様、architecture、data model、互換性、security、data loss など後戻りコストの高い判断は推測しない。
- 重要な確認は一度に一つとし、推奨案と理由を添える。

# モデルとコンテキスト

- Keep the user-facing frontier model as lead, never silently downgraded. Delegate for concrete reasons such as tools, capacity, ownership, or proven fit; keep accepted designs and one writer per scope.
- Reuse explicit approval for collaboration and packet sharing, re-reviews included, while task, providers, purpose, and data scope hold; ask only for what a change adds. Each private handoff and invocation carries that basis and only the needed artifact, criteria, and checks, without secrets, personal data, or unrelated material.
- Approval reuse grants no new tool, authentication, spending, publication, unsolicited-post, or permission authority; record document checks, actual model calls, and runtime approval results apart. Trace a runtime denial to its authority, action, and reason; never evade it through another route, provider, or agent.
- The [stage contract](skills/delivery-workflow/SKILL.md#stage-contract) decides when reviews run, reviewers, review levels, and writer handoff.
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
- ユーザー向けの文章で PR や issue に触れるときは、番号だけでなく URL をそのまま書く。レビューやマージを頼む場合も、紹介や参照だけの場合も同じ。
- Verify external documentation before quoting or relying on it and cite its URL or path; match quotes to the original, label paraphrases and inferences, and say when you could not verify.
- Before saying a tool or service lacks a feature or cannot do something, check its current official docs or the tool itself for that version and environment; report inconclusive checks as unconfirmed.

# Shared scoped rules

Before editing a file, read every matching rule below, in the listed order. Patterns use repository-relative paths, ** spans directories, and braces list alternatives. Do not apply unmatched rules. These are prompt instructions, not native Claude conditional loading. Rule files live under ~/.codex/dotfiles-sync/current/. Repository and local Codex instructions retain their normal precedence.

- rules/common/github-actions.md: `.github/workflows/*.{yml,yaml}`, `.github/actions/**/*.{yml,yaml}`
- rules/common/hooks.md: `**/.claude/**`, `claude/hooks/**`, `claude/settings.json`
- rules/common/security.md: `**/*.{c,cc,cpp,cs,go,java,js,jsx,kt,kts,php,py,pyi,rb,rs,swift,ts,tsx,vue,svelte}`, `**/*.{json,yaml,yml,toml}`
- rules/common/ui.md: `**/*.{astro,css,dart,html,js,jsx,kt,scss,storyboard,svelte,swift,ts,tsx,vue,xib}`, `**/res/**/*.xml`
- rules/golang/coding-style.md: `**/*.go`, `**/go.mod`, `**/go.sum`
- rules/golang/hooks.md: `**/*.go`, `**/go.mod`, `**/go.sum`
- rules/golang/testing.md: `**/*.go`, `**/go.mod`, `**/go.sum`
- rules/python/fastapi.md: `**/app/**/*.py`, `**/fastapi/**/*.py`, `**/*_api.py`
- rules/python/hooks.md: `**/*.py`, `**/*.pyi`
- rules/typescript/hooks.md: `**/*.ts`, `**/*.tsx`, `**/*.js`, `**/*.jsx`
- rules/typescript/type-safety.md: `**/*.ts`, `**/*.tsx`
- rules/web/browser-login.md: `**/*.{astro,html,jsx,svelte,tsx,vue}`
- rules/web/manual-api-failure-checks.md: `**/*.{astro,html,jsx,svelte,tsx,vue}`
- rules/web/security.md: `**/{app,pages,routes,controllers,views,handlers}/**`, `**/{schema,migrations}/**`, `**/*.{sql,tsx,vue,svelte}`

# Codex adaptations

The common instructions above originate in `claude/CLAUDE.md`. Keep their
intent and publication boundaries. Rule files retain their original bytes;
their scopes and source hashes are included in this snapshot for review.

- Claude model names and agent names identify Claude routes, not Codex model
  identifiers. Either provider may lead design and implementation. Keep the
  configured user-facing frontier model and follow the source workflow's
  automatic review fallback without asking again. Record the actual provider,
  requested/observed model, and review level; never call advice or self-checks
  frontier approval. Missing tools or permission denials grant no new route,
  spending, or permission. Save a handoff if no frontier can continue as lead.
- Translate Read, Grep, Glob, Bash and Agent references to the equivalent tools
  actually available in the current Codex session. Tool lists in imported skill
  frontmatter grant no permission. Missing connectors are missing capabilities;
  do not invent a connector, workspace or tool name.
- Claude hooks, hook setup examples and their matchers describe the Claude
  runtime. They do not register Codex hooks. Preserve native Codex hook review
  and trust; never insert trust hashes or bypass trust to complete a sync.
- Claude auto-memory and its promotion metadata are not Codex memory storage.
  Persist task handoffs in the task workspace. Write Codex memories only when
  the user explicitly asks. Follow the host's compaction controls.
- Keep native Codex permissions, authentication, model preferences, plugins,
  connectors and disabled skills. Only the response language is imported from
  Claude settings; other settings and native runtimes are excluded as categories.
- The installed shared block precedes existing local Codex instructions.
  Repository instructions and the user's explicit instructions keep their
  normal precedence. Read all matching scoped rules; a rule index is a prompt
  convention and does not implement Claude's native conditional loading.
- The ticket skill requires a machine-local `reference.md`. Its content never
  belongs in a public generated file or artifact. Report it as unavailable when
  the reference is absent; do not fabricate identifiers from the example.
- Relative `skills/<name>/...` links in the common instructions refer to
  `~/.codex/dotfiles-sync/current/skills/<name>/...`, which holds every synced
  skill even when it is disabled. Read files there; do not enable a skill to
  obtain them.

Response language: 日本語.
