# dotfiles

[![CI](https://github.com/WatanabeToshimitsu/dotfiles/actions/workflows/ci.yml/badge.svg)](https://github.com/WatanabeToshimitsu/dotfiles/actions/workflows/ci.yml)

個人の開発環境と、Claude Code・Codexの作業ルールを管理するリポジトリです。
シェルやエディタの設定、ツールの導入、エージェントの運用・診断をまとめています。macOSを主な対象とし、Linux・WSL2にも対応しています。

## 目次

- [開発環境・コマンド](#key-tools)
- [セットアップ](#setup)
- [設定の再適用](#reapply-settings)
- [AIエージェントの設定](#agent-configuration)
  - [CodexとClaudeのハーネスの同期](#codex-configuration-sync)
  - [外部スキルの更新](#agent-skills)
  - [PR作成時の確認](#pr-publication-approval)
  - [通知](#notifications)
- [エージェント環境の診断](#agent-diagnostics)
- [秘密情報の利用](#secrets)
- [リポジトリ構成](#configuration-storage-strategy)
- [このリポジトリのGitHub設定](#public-repository-safety)

<a id="key-tools"></a>

## 開発環境・コマンド

| 用途 | ツール |
| --- | --- |
| ターミナルカスタマイズ | Zsh + [Zinit](https://github.com/zdharma-continuum/zinit) |
| プロンプト | [oh-my-posh](https://ohmyposh.dev/) |
| ファイル検索・プレビュー | [fzf](https://github.com/junegunn/fzf) + [ripgrep](https://github.com/BurntSushi/ripgrep) + [bat](https://github.com/sharkdp/bat) |
| リポジトリ・ディレクトリ移動 | [ghq](https://github.com/x-motemen/ghq) + fzf、[zoxide](https://github.com/ajeetdsouza/zoxide) |
| ファイル一覧 | [lsd](https://github.com/lsd-rs/lsd) |
| ターミナル・作業ペイン | [Ghostty](https://ghostty.org) + [herdr](https://herdr.dev) |
| エディタ | [Neovim](https://neovim.io) + [LazyVim](https://www.lazyvim.org)、VS Code |
| ファイル管理 | [yazi](https://yazi-rs.github.io) |
| Node.jsのバージョン管理 | [Volta](https://volta.sh/) |
| Pythonのバージョン管理 | [pyenv](https://github.com/pyenv/pyenv) |

以下のコマンドで、リポジトリの移動や整理ができます。

<a id="notable-aliases"></a>

| コマンド | やりたいこと |
| --- | --- |
| `gcd` | ghqで管理するリポジトリを選んで移動 |
| `gcode` | リポジトリを選んでVS Codeで開く |
| `gvim` | リポジトリを選んでNeovimで開き、シェルの作業ディレクトリも移す |
| `y` | yaziでファイルを探し、終了時に選んだディレクトリへ移動 |
| `gb-prune` | マージ済みブランチを整理。squash mergeにも対応 |
| `ghq-rm` | ghqで管理するリポジトリを対話的に削除 |

<a id="setup"></a>
<a id="macos--linux--wsl2"></a>

## セットアップ

以下のコマンドで、ツールの導入と設定の反映を行います。

```bash
git clone https://github.com/WatanabeToshimitsu/dotfiles.git ~/dotfiles
cd ~/dotfiles
bash install.sh
```

端末固有の設定は`~/.zshrc.local`に置いてください。このリポジトリでは追跡しません。

<a id="reapply-settings"></a>

## 設定の再適用

以下のコマンドで、パッケージを導入せずに設定のリンクを張り直せます。

```bash
bash install.sh --symlinks-only
```

Headroomだけを再設定する場合は、以下のコマンドを使ってください。

```bash
./install.sh --headroom-only
```

<a id="agent-configuration"></a>

## AIエージェントの設定

共通の作業方針は[`claude/CLAUDE.md`](claude/CLAUDE.md)で管理しています。`rules/`には分野別のルール、`skills/`には作業手順、`agents/`には補助エージェントの定義、`hooks/`には操作時の検査や通知の処理があります。

| 機能 | 内容・使い方 |
| --- | --- |
| 実装とレビュー | [`delivery-workflow`](claude/skills/delivery-workflow/SKILL.md)と[`code-review`](claude/skills/code-review/SKILL.md)に沿って、設計・実装を独立したエージェントがレビュー |
| 出力の圧縮 | [長いツール出力を短縮し、必要な箇所を再取得](docs/agent-operations.md#claude-tool-output-compaction) |
| 応答量の調整 | [Headroomで応答の長さを調整し、削減効果を測定](docs/agent-operations.md#headroom-proxy) |
| 作業の隔離 | [macOS向けBash sandboxを必要に応じて利用](docs/agent-operations.md#claude-bash-sandbox-canary) |
| 学びの共有 | [ClaudeのAuto Memoryと、共通ルールへの反映状況を管理](docs/agent-operations.md#claude-auto-memory) |
| 定期実行 | [Loopで任せる作業を計画](docs/agent-operations.md#loop-contracts)。dotfilesでは試行・検証段階 |

<a id="codex-configuration-sync"></a>

### CodexとClaudeのハーネスの同期

Codexの共通指示・ルール・スキルは、`claude/`を原本として生成しています。`codex/generated/`は手動編集しないでください。

以下のコマンドで、適用内容の確認とCodexへの反映ができます。

```bash
bash install.sh --codex-only --dry-run
bash install.sh --codex-only
```

詳細は[Codex同期ガイド](codex/README.md)を参照してください。

<a id="agent-skills"></a>

### 外部スキルの更新

外部スキルは`install.sh`で導入します。導入済みの`natural-japanese`を更新する場合は、以下のコマンドを使ってください。

```bash
npx skills update natural-japanese -g -y
```

<a id="pr-publication-approval"></a>

### PR作成時の確認

エージェントは、作成先・タイトル・本文・公開する全コミットを準備し、秘密情報などの検査結果を示してから、PR作成の直前に承認を求めます。依頼範囲内の通常のcommit・pushは、その都度の確認なしで進みます。詳細は[PR公開前の確認](docs/pr-approval.md)を参照してください。

<a id="notifications"></a>

### 通知

Pushover通知を使う場合は、`PUSHOVER_API_TOKEN`と`PUSHOVER_USER_KEY`を`~/.zshrc.local`に設定してください。有効にすると、Claudeの通知本文がPushover APIへ送信されます。

<a id="agent-diagnostics"></a>

## エージェント環境の診断

以下のコマンドで、Headroom・MCP・Claude Codeのバージョン・Codex設定の同期状態を確認できます。

```bash
~/.shell-utils/dotfiles-doctor.sh --harness-only
```

週次診断の確認方法と、機能別の調べ方は[エージェント運用ガイド](docs/agent-operations.md#agent-diagnostics)を参照してください。

<a id="secrets"></a>

## 秘密情報の利用

APIキー・トークン・秘密鍵や、秘密情報を含む端末の設定ファイルをコミットしないでください。テンプレートにも平文の秘密情報を置かないでください。

秘密情報をシェルから使う場合は、[`templates/zshrc.local.tpl`](templates/zshrc.local.tpl)に1Passwordの`op://`参照を記入し、[1Password CLI](https://developer.1password.com/docs/cli/)へログインしてから以下を実行してください。`~/.zshrc.local`が生成されます。既存ファイルを置き換える場合は`--force`を付けてください。

```bash
dotfiles-secrets.sh
```

<a id="whats-included"></a>
<a id="configuration-storage-strategy"></a>

## リポジトリ構成

設定の原本をこのリポジトリに置き、`install.sh`で各ツールの読み込み先へ反映する構成です。

| 場所 | 役割・反映先 |
| --- | --- |
| [`.zshrc`](.zshrc)・[`.bashrc`](.bashrc)など | シェルの設定。ホームディレクトリへリンク |
| [`.vimrc`](.vimrc)・[`.tmux.conf`](.tmux.conf) | Vimとtmuxの設定。ホームディレクトリへリンク |
| [`.config/`](.config/) | Ghostty・herdr・Neovim・yaziなどの設定。`~/.config/`へ反映 |
| [`.shell-utils/`](.shell-utils/) | 診断・更新・リポジトリ整理の補助コマンド。`~/.shell-utils/`へリンク |
| [`oh-my-posh-theme/`](oh-my-posh-theme/) | プロンプトの見た目。ホームディレクトリへリンク |
| [`claude/`](claude/) | Claude Codeの共通指示・ルール・スキル・フック。`~/.claude/`へ反映 |
| [`codex/`](codex/) | Claudeの共通設定をCodexへ同期する方針と生成結果 |
| [`vscode/`](vscode/) | macOSのVS Code設定。キー設定はリンク、設定本体は初回コピー |
| [`herdr-plugins/`](herdr-plugins/) | 自作のherdrプラグイン |
| [`Brewfile`](Brewfile) | Homebrewで導入するツール・アプリの一覧 |
| [`install.sh`](install.sh)・[`uninstall.sh`](uninstall.sh)・[`symlink-manifest.sh`](symlink-manifest.sh) | 導入・解除の処理と、管理するリンクの一覧 |
| [`scripts/`](scripts/) | Codex設定の生成・適用や、作業状況の収集処理 |
| [`docs/`](docs/)・[`templates/`](templates/) | 運用ガイドと、端末・プロジェクトごとの設定ひな形 |
| [`test/`](test/)・[`.github/workflows/`](.github/workflows/) | テストと、このリポジトリのCI |

ルートの[`CLAUDE.md`](CLAUDE.md)と[`AGENTS.md`](AGENTS.md)は、このリポジトリを変更するエージェント向けの指示です。各プロジェクトに適用する共通指示は[`claude/CLAUDE.md`](claude/CLAUDE.md)で管理しています。

<a id="public-repository-safety"></a>

## このリポジトリのGitHub設定

このリポジトリのCIでは、PRとmainへのpushを対象に、設定ファイルの検証、インストーラー・フックのテスト、Codex生成物の整合性確認、GitleaksによるGit履歴全体の秘密情報検査を実行します。検査内容は[`.github/workflows/`](.github/workflows/)で管理しています。
