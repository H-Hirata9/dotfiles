# dotfiles

Claude Code / OpenAI Codex / GitHub Copilot / Antigravity の共通設定を管理するリポジトリ。

## 構成

```
dotfiles/
├── rules/                     # 各ルールの実体（ここを編集する）
│   ├── coding.md
│   ├── git.md
│   ├── security.md
│   ├── workflow.md
│   ├── tone/                  # 口調プリセット（1つだけ有効化）
│   │   ├── associate_girl-jp.md
│   │   ├── concise-en.md
│   │   ├── formal-jp.md
│   │   ├── kansai-ojisan-jp.md
│   │   └── tundere-jp.md
│   ├── output/                # 出力フォーマットプリセット
│   │   ├── minimal.md
│   │   └── rich.md
│   └── tooling/               # ツール別規約
│       ├── bun.md
│       └── uv.md
├── codex/
│   └── AGENTS.md              # setup.sh が自動生成（直接編集しない）
├── claude/
│   ├── CLAUDE.md              # Claude Code 専用設定
│   └── settings.json          # Claude Code 設定
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
2. 以下のシンボリックリンクを作成する

| 配置先 | 実体 |
|--------|------|
| `~/.claude/CLAUDE.md` | `claude/CLAUDE.md` |
| `~/.claude/settings.json` | `claude/settings.json` |
| `~/.codex/AGENTS.md` | `codex/AGENTS.md` |
| `~/.claude/rules` | `rules/` |

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
# rules/tone/ から使いたいファイルを選ぶ
```

Claude Code 固有の設定は `claude/CLAUDE.md` に追記する。

## GitHub Copilot / Antigravity（プロジェクト単位）

プロジェクトの `.github/copilot-instructions.md` や `AGENTS.md` に
`codex/AGENTS.md` の内容をコピーして使う（またはシンボリックリンクを張る）。
