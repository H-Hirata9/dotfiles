# dotfiles

Claude Code / OpenAI Codex / GitHub Copilot / Antigravity の共通設定を管理するリポジトリ。

> 新端末を裸の状態から動くADAにする手順は **[BOOTSTRAP.md](BOOTSTRAP.md)** を参照。

## 構成

```
dotfiles/
├── rules/                     # 各ルールの実体（~/.claude/rules へ junction。配下は全て自動ロードされる）
│   ├── coding.md
│   ├── git.md
│   ├── security.md
│   ├── workflow.md
│   ├── tone/                  # 口調プリセット（有効化中。既定=ada-jp）
│   │   └── ada-jp.md
│   └── tooling/               # ツール別規約
│       ├── bun.md
│       └── uv.md
├── rules-presets/             # 未使用のトーン/出力プリセット置き場（自動ロードされない。使うときだけ rules/ 配下へ移すか個別 @import する）
│   ├── tone/
│   │   ├── concise-en.md
│   │   ├── consultant-jp.md
│   │   ├── formal-jp.md
│   │   ├── kansai-ojisan-jp.md
│   │   └── tundere-jp.md
│   └── output/
│       ├── minimal.md
│       └── rich.md
├── git-hooks/
│   └── pre-commit            # gitleaks による秘密スキャン（global core.hooksPath で全リポに適用）
├── codex/
│   └── AGENTS.md              # setup.sh が自動生成（直接編集しない）
├── claude/
│   ├── CLAUDE.md              # Claude Code 専用設定
│   ├── settings.json          # Claude Code 設定
│   ├── skills/                # ADA 自作 skill の実体（vendor skill は含めない）
│   └── hooks/                 # Claude hooks の実体（ada-guard 等。ログは gitignore）
├── BOOTSTRAP.md               # 新端末セットアップ手順（層0 + 再認証 runbook）
├── setup.sh                   # WSL / Linux 用セットアップスクリプト
└── setup.ps1                  # Windows (PowerShell) 用セットアップスクリプト
```

## セットアップ

### WSL / Linux

```bash
bash setup.sh           # 通常実行
bash setup.sh --dry-run # 変更内容の確認のみ（実際には何もしない）
bash setup.sh --force   # 既存の通常ファイルをバックアップして上書き
```

### Windows (PowerShell)

```powershell
.\setup.ps1 -DryRun   # 確認のみ
.\setup.ps1 -Force    # 実行（既存ファイルをバックアップして上書き）
```

## setup.sh の動作

1. `rules/` 以下の各ファイルを結合して `codex/AGENTS.md` を生成する
2. `git config --global core.hooksPath` を `git-hooks/` に向け、全リポの commit 時に gitleaks で秘密スキャンを行う（setup.ps1 は gitleaks を winget で自動導入。setup.sh は導入チェックのみ）
3. 以下のシンボリックリンクを作成する

| 配置先 | 実体 |
|--------|------|
| `~/.claude/CLAUDE.md` | `claude/CLAUDE.md` |
| `~/.claude/settings.json` | `claude/settings.json` |
| `~/.codex/AGENTS.md` | `codex/AGENTS.md` |
| `~/.gemini/GEMINI.md` | `gemini/GEMINI.md` |
| `~/.claude/rules` | `rules/`（junction） |
| `~/.claude/skills/<自作>` | `claude/skills/<自作>`（per-skill junction。vendor skillは対象外） |
| `~/.claude/hooks` | `claude/hooks/`（junction。`*.log` は gitignore） |

### smart_link の挙動

| ターゲットの状態 | `--force` なし | `--force` あり |
|-----------------|----------------|----------------|
| 存在しない | リンク作成 | リンク作成 |
| 正しいシンボリックリンク | スキップ | スキップ |
| 古い / 間違ったシンボリックリンク | 自動更新 | 自動更新 |
| 通常ファイル / ディレクトリ | スキップ | バックアップ後に上書き |

バックアップは `<target>.bak.YYYYMMDDHHMMSS` の形式で同じ場所に保存される。

## 設定を変更する

`rules/` 以下の各ファイルを編集してから `setup.sh` を再実行すると `codex/AGENTS.md` が再生成される。

```bash
# 例: 口調を変えたい場合は CLAUDE.md の @import 行を変更する
# rules/tone/ (自動ロード) または rules-presets/tone/ (未使用プリセット) から使いたいファイルを選ぶ
```

Claude Code 固有の設定は `claude/CLAUDE.md` に追記する。

## プロジェクト単位での Claude Code 設定

新規プロジェクトに `.claude/CLAUDE.md` を素早く生成できる。

### WSL / Linux

```bash
bash ~/dotfiles/setup.sh init-project                        # base テンプレート（カレントディレクトリ）
bash ~/dotfiles/setup.sh init-project python                 # Python + uv
bash ~/dotfiles/setup.sh init-project typescript             # TypeScript + bun
bash ~/dotfiles/setup.sh init-project python /path/to/proj  # パス指定
bash ~/dotfiles/setup.sh init-project python --dry-run       # 確認のみ
```

### Windows (PowerShell)

```powershell
.\setup.ps1 -InitProject                                    # base テンプレート（カレントディレクトリ）
.\setup.ps1 -InitProject -Template python                   # Python + uv
.\setup.ps1 -InitProject -Template typescript               # TypeScript + bun
.\setup.ps1 -InitProject -Template python -ProjectPath C:\work\myapp
.\setup.ps1 -InitProject -Template python -DryRun           # 確認のみ
```

生成されるファイル:
- `<project>/.claude/CLAUDE.md` — Claude Code 用（`[PROJECT_NAME]` 等を書き換える）
- `<project>/.agents/rules/project.md` — Antigravity 用プロジェクトコンテキスト
- `<project>/.agents/rules/tooling.md` — Antigravity 用ツール規約（python/typescript のみ）
- `<project>/.gitignore` — Claude のローカルファイルを除外するエントリを追記

### テンプレート一覧

| テンプレート | 用途 |
|-------------|------|
| `base` | 言語非依存の最小構成 |
| `python` | Python + uv（`@~/.claude/rules/tooling/uv.md` 参照） |
| `typescript` | TypeScript + bun（`@~/.claude/rules/tooling/bun.md` 参照） |

`templates/project/` 以下に `.md` ファイルを追加すれば独自テンプレートを作れる。

### 階層構造

| スコープ | パス | 説明 |
|---------|------|------|
| グローバル | `~/.claude/CLAUDE.md` | 口調・コーディング規約など（全プロジェクト共通） |
| プロジェクト | `<project>/.claude/CLAUDE.md` | プロジェクト固有の文脈・制約（git で共有） |
| ローカル | `<project>/CLAUDE.local.md` | 個人オーバーライド（gitignore） |

プロジェクト CLAUDE.md には固有の内容だけ書く。共通ルールはグローバル設定で自動適用される。

## DeepSeek バックエンドへの切り替え

`scripts/Use-DeepSeek.ps1` を使うと、Claude Code のバックエンドを一時的に DeepSeek に切り替えられる。

### 準備

`~/.claude/.env.deepseek` を作成してAPIキーを記載する（git には入れない）:

```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxx
```

### 使い方（PowerShell）

```powershell
# DeepSeek に切り替え（ドットソース必須）
. ~/dotfiles/scripts/Use-DeepSeek.ps1

# このシェルで claude を起動すると DeepSeek バックエンドで動く
claude

# Anthropic に戻す
. ~/dotfiles/scripts/Use-DeepSeek.ps1 -Mode Unset
```

> ドットソース（`. スクリプト`）で実行しないと現在のシェルに環境変数が反映されない。

別の `.env` ファイルを指定したい場合:

```powershell
. ~/dotfiles/scripts/Use-DeepSeek.ps1 -EnvFile C:\path\to\.env
```

## GitHub Copilot / Antigravity（プロジェクト単位）

プロジェクトの `.github/copilot-instructions.md` や `AGENTS.md` に
`codex/AGENTS.md` の内容をコピーして使う（またはシンボリックリンクを張る）。
