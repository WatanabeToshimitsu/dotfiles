# dotfiles

[![CI](https://github.com/WatanabeToshimitsu/dotfiles/actions/workflows/ci.yml/badge.svg)](https://github.com/WatanabeToshimitsu/dotfiles/actions/workflows/ci.yml)

個人の開発環境と、Claude Code・Codexの作業ルールを管理するリポジトリです。
シェルやエディタの設定、必要なツールの導入、エージェントの運用・診断をまとめています。macOSを主な対象とし、Linux・WSL2にも対応しています。

全体を把握するには「構成と設定の反映先」、日常の操作を知るには「普段使うツールとコマンド」から読んでください。詳しい運用手順は別ページにまとめています。

## 目次

- [構成と設定の反映先](#configuration-storage-strategy)
- [普段使うツールとコマンド](#key-tools)
- [セットアップと更新](#setup)
  - [新しい環境への導入](#macos--linux--wsl2)
  - [設定の再適用とCodexの更新](#codex-configuration-sync)
  - [外部スキルの更新](#agent-skills)
  - [Codespacesでの利用](#codespaces)
- [AIエージェントの設定](#agent-configuration)
- [秘密情報と公開時のルール](#secrets)
- [詳しい運用ガイド](#guides)

<a id="whats-included"></a>
<a id="configuration-storage-strategy"></a>

## 構成と設定の反映先

設定の原本をこのリポジトリに置き、`install.sh`が各ツールの読み込み先につなぎます。多くはシンボリックリンクなので、原本の変更が利用側にも反映されます。

| 場所 | 役割・反映先 |
| --- | --- |
| [`.zshrc`](.zshrc) | メインのシェル、Zshの設定。`~/.zshrc`へリンク |
| [`.bashrc`](.bashrc)・[`.bash_profile`](.bash_profile) | Bashの設定。NVM・Volta・Docker関連の設定を含む |
| `.zprofile`・`.zshenv`・`.profile`・[`.shell-common`](.shell-common) | シェル起動時の環境設定。ホームディレクトリへリンク |
| [`.vimrc`](.vimrc)・[`.tmux.conf`](.tmux.conf) | Vimとtmuxの設定。Neovimやherdrがない接続先でも使う予備の環境 |
| [`.config/`](.config/) | Gitの除外設定、GitHub CLI、Ghostty、herdr、Husky、Neovim、yazi。`~/.config/`へ反映 |
| [`.shell-utils/`](.shell-utils/) | 診断・更新・リポジトリ整理などの補助コマンド。`~/.shell-utils/`へディレクトリごとリンク |
| [`oh-my-posh-theme/`](oh-my-posh-theme/) | プロンプトの見た目。`~/oh-my-posh-theme/`へリンク |
| [`claude/`](claude/) | Claude Codeの共通指示・ルール・スキル・フック。`~/.claude/`へファイル単位でリンク |
| [`codex/`](codex/) | Claudeの共通指示をCodex向けに変換する方針と生成結果。専用の同期処理で適用 |
| [`vscode/`](vscode/) | macOSのVS Codeユーザー設定。キー設定はリンク、設定本体は初回コピー |
| [`herdr-plugins/`](herdr-plugins/) | 自作のherdrプラグイン。`herdr plugin link`で登録し、リポジトリの変更を直接反映 |
| [`Brewfile`](Brewfile) | Homebrewで導入するCLI・アプリ・VS Code拡張の一覧 |
| [`install.sh`](install.sh)・[`uninstall.sh`](uninstall.sh)・[`symlink-manifest.sh`](symlink-manifest.sh) | 導入・解除の処理と、管理するリンクの一覧 |
| [`scripts/`](scripts/) | Codex設定の生成・適用や、作業状況の収集処理 |
| [`docs/`](docs/)・[`templates/`](templates/) | 運用ガイドと、端末・プロジェクトごとに使うひな形 |
| [`test/`](test/)・[`.github/workflows/`](.github/workflows/) | 導入処理やフックのテスト、設定・秘密情報などの自動検査 |

ルートの[`CLAUDE.md`](CLAUDE.md)は、このリポジトリを変更するエージェント向けの指示です。[`AGENTS.md`](AGENTS.md)からも参照します。一方、[`claude/CLAUDE.md`](claude/CLAUDE.md)は、各プロジェクトで使う共通指示の原本です。

ツールの設定は、原則としてXDGの配置先である`.config/`に置きます。独自の保存先を使うツールは、`claude/`のように専用ディレクトリで管理します。VS Codeの反映先は`~/Library/Application Support/Code/User/`です。

<a id="key-tools"></a>

## 普段使うツールとコマンド

| 用途 | ツールと構成 |
| --- | --- |
| コマンド操作 | Zsh + [Zinit](https://github.com/zdharma-continuum/zinit)。プラグインは遅延読み込み |
| プロンプト | [oh-my-posh](https://ohmyposh.dev/)。OS・メモリ使用量・実行時間・Gitの状態を表示 |
| ファイル検索・プレビュー | [fzf](https://github.com/junegunn/fzf) + [ripgrep](https://github.com/BurntSushi/ripgrep) + [bat](https://github.com/sharkdp/bat) |
| リポジトリ・ディレクトリ移動 | [ghq](https://github.com/x-motemen/ghq) + fzf、[zoxide](https://github.com/ajeetdsouza/zoxide)の`z`・`zi` |
| ファイル一覧・内容表示 | [lsd](https://github.com/lsd-rs/lsd)で一覧、batで内容、ripgrepで検索 |
| 作業画面 | ターミナルの[Ghostty](https://ghostty.org)と、エージェントの作業ペインを管理する[herdr](https://herdr.dev)。操作のprefixキーは`cmd+space` |
| 編集 | [Neovim](https://neovim.io) + [LazyVim](https://www.lazyvim.org)を`$EDITOR`に設定。vscodevimのキー操作を移植し、プラグインは`lazy-lock.json`で固定 |
| ファイル管理 | [yazi](https://yazi-rs.github.io)。画像・動画・PDFをプレビュー |
| Node.js | [Volta](https://volta.sh/)。Zshではnvmを使わない |
| Python | [pyenv](https://github.com/pyenv/pyenv)。初回呼び出しで関数を解除する方式で初期化を遅延 |

<a id="notable-aliases"></a>

| やりたいこと | コマンド |
| --- | --- |
| ghqで管理するリポジトリを選んで移動 | `gcd` |
| リポジトリを選んでVS Codeで開く | `gcode` |
| リポジトリを選んでNeovimで開き、シェルの作業ディレクトリも移す | `gvim` |
| yaziでファイルを探し、終了時に選んだディレクトリへ移動 | `y` |
| マージ済みブランチを整理。`gh`でsquash mergeも判定 | `gb-prune` |
| ghqで管理するリポジトリを対話的に削除 | `ghq-rm` |

<a id="terminal-file-workflow"></a>

herdr内では`prefix+y`で一時ペインにyaziを開き、`Enter`で`$EDITOR`へ渡せます。`nvim`でLazyVimを起動し、`<leader>fy`でエディタ内のyazi.nvimを開きます。

Ghosttyとherdrはkitty graphics protocolに対応しており、yaziとNeovimで画像を表示する構成です。Neovimのsnacks.imageはPNGを直接表示し、JPG・WebP・GIFにはImageMagickが必要です。通常のVimは`vi`で使え、設定はUTF-8・2スペース・大文字小文字を考慮する検索を基本としています。VS Codeも引き続き利用できます。

<a id="setup"></a>

## セットアップと更新

<a id="macos--linux--wsl2"></a>

### 新しい環境への導入

```bash
git clone https://github.com/WatanabeToshimitsu/dotfiles.git ~/dotfiles
cd ~/dotfiles
bash install.sh
```

macOSではHomebrewを必要に応じて導入し、`brew bundle`を実行します。Linuxではapt・yum・dnfでパッケージを導入し、root以外ではHomebrewも使います。

共通の処理で、対象を明示した設定ファイルだけをホームディレクトリへリンクします。`.git`やプロジェクト用の`.claude`などはリンクしません。外部のエージェントスキル、herdrの連携・プラグインと`worktree-setup`、CLIツールやHeadroomも設定します。macOSではVS Codeの設定と週次の環境診断も用意します。

端末固有の設定は`~/.zshrc.local`に置きます。Zshから読み込みますが、このリポジトリでは追跡しません。

<a id="codex-configuration-sync"></a>

### 設定の再適用とCodexの更新

パッケージやツールを導入せず、管理対象のリンクだけを張り直すには次を実行します。

```bash
bash install.sh --symlinks-only
```

Codexの共通指示・ルール・スキルは、`claude/`を原本として生成します。`codex/generated/`は手で編集しません。初回は適用内容を確認してから反映します。

```bash
bash install.sh --codex-only --dry-run
bash install.sh --codex-only
```

以後は`dotfiles-update`でmainを取得し、fast-forward更新後にコミット済みのCodex設定を適用します。適用後は新しいCodexタスクを開きます。認証・権限・モデル・フックの信頼設定など、Codex固有の設定は端末側に残します。適用条件・競合・復元手順は[Codex同期ガイド](codex/README.md)を参照してください。

<a id="agent-skills"></a>

### 外部スキルの更新

`install.sh`の`setup_agent_skills`は、未導入の共通スキルを公開GitHubリポジトリから復元します。たとえば日本語の文章を整える`natural-japanese`は[`coji/natural-japanese`](https://github.com/coji/natural-japanese)から導入し、このリポジトリには同梱しません。スキル管理のlockに登録された後は、次のコマンドで更新します。

```bash
npx skills update natural-japanese -g -y
```

<a id="codespaces"></a>

### Codespacesでの利用

GitHubの「Settings → Codespaces」で「Automatically install dotfiles」を有効にし、このリポジトリを選びます。Codespace作成時に`install.sh`が実行されます。端末固有の設定先は、ここでも`~/.zshrc.local`です。

<a id="agent-configuration"></a>
<a id="claude-tool-output-compaction"></a>
<a id="claude-bash-sandbox-canary"></a>
<a id="claude-auto-memory"></a>
<a id="loop-contracts"></a>
<a id="headroom-proxy"></a>

## AIエージェントの設定

[Claude Code](https://claude.ai/code)の設定は`claude/`に集約しています。`rules/`は作業時の規則、`skills/`は再利用する作業手順、`agents/`は補助エージェントの定義です。`hooks/`には、特定の操作時に実行する検査や通知の処理を置いています。

| 目的 | 仕組み・詳細 |
| --- | --- |
| 作業方針とレビュー手順をそろえる | [`claude/CLAUDE.md`](claude/CLAUDE.md)、[`delivery-workflow`](claude/skills/delivery-workflow/SKILL.md)、[`code-review`](claude/skills/code-review/SKILL.md)。共通部分をCodexにも展開 |
| 大きなツール出力で会話が埋まるのを防ぐ | [出力の圧縮と再取得](docs/agent-operations.md#claude-tool-output-compaction)。全文はローカルに7日間保存 |
| 応答の出力量を調整し、削減効果を確かめる | [Headroom](docs/agent-operations.md#headroom-proxy)。ローカルプロキシと比較測定の設定 |
| 強い隔離が必要な作業で試す | [macOS向けsandbox canary](claude/SANDBOX.md)。通常のAutoモードとは別の、任意で使う試行環境 |
| プロジェクトの学びを共通指示に反映する | [Auto Memory](claude/AUTO-MEMORY.md)。記憶からルール・スキルへの反映状況を診断 |
| 定期実行に任せる範囲を決める | [Loop契約](docs/agent-operations.md#loop-contracts)。承認済みの契約がないプロジェクトは読み取り専用 |

エージェント環境の診断は`~/.shell-utils/dotfiles-doctor.sh --harness-only`で実行します。Headroomへの接続、MCP接続、Claude Codeのバージョン差分を調べます。具体的な確認・復旧コマンドは[運用ガイド](docs/agent-operations.md)にまとめています。

<a id="secrets"></a>
<a id="pr-publication-approval"></a>
<a id="public-repository-safety"></a>

## 秘密情報と公開時のルール

このリポジトリは公開用です。端末固有の`~/.zshrc.local`・`~/.npmrc`、VS Codeの利用中の設定変更、内部ホスト名、herdr-mirrorの`hosts.toml`は追跡しません。`.npmrc`がない場合だけ、`install.sh`が[`.npmrc.example`](.npmrc.example)から作成します。

秘密情報は、[`templates/zshrc.local.tpl`](templates/zshrc.local.tpl)の`op://`参照から`dotfiles-secrets.sh`で`~/.zshrc.local`へ書き出します。導入後はPATHから実行でき、ログイン済みの[1Password CLI](https://developer.1password.com/docs/cli/)が必要です。テンプレートに平文の秘密情報を置かないでください。既存ファイルは`--force`なしでは上書きせず、書き出し先の権限は`0600`です。1Passwordでの生成に失敗した場合は元のファイルを残します。

Pushover通知は、`PUSHOVER_API_TOKEN`と`PUSHOVER_USER_KEY`の両方が環境変数にある場合だけ有効です。値は`~/.zshrc.local`だけに置きます。有効にするとClaudeの通知本文をPushover APIへ送信します。通知の失敗やタイムアウトでClaudeの作業は止めません。

エージェントは、PRの公開内容を確認し、作成の直前に毎回ユーザーの承認を得ます。通常のpushは許可し、強制pushやリモート削除はブロックします。Codex CLIでは実行時のレビューが自動になる場合があるため、会話中の確認が必要です。適用範囲は[PR公開前の確認](docs/pr-approval.md)を参照してください。

PRとmainへのpushでは、Git履歴全体の秘密情報検査などをCIで実行する構成です。除外対象や検査の限界は[公開リポジトリの保護](docs/agent-operations.md#public-repository-safety)に記載しています。

<a id="external-dependency-policy"></a>
<a id="guides"></a>

## 詳しい運用ガイド

| 知りたいこと | 資料 |
| --- | --- |
| 出力圧縮、Headroom、Loop契約、診断・復旧 | [エージェント運用ガイド](docs/agent-operations.md) |
| 外部ツールのバージョン固定と更新方針 | [外部依存の管理](docs/agent-operations.md#external-dependency-policy) |
| ClaudeからCodexへの同期・競合・復元 | [Codex同期ガイド](codex/README.md)・[検証記録](codex/verification.md) |
| PR公開前に確認する内容と、制御できる範囲 | [PR公開前の確認](docs/pr-approval.md) |
| sandboxの対象範囲・検証・元に戻す手順 | [Sandbox Canary](claude/SANDBOX.md) |
| Auto Memoryの検証済みの挙動と、過去データの扱い | [Auto Memory](claude/AUTO-MEMORY.md) |
| 定期実行を許可する条件の書き方 | [Loop契約テンプレート](templates/loop-contract.md)・[dotfilesでの記入例](docs/dotfiles-loop-contract.example.md) |
