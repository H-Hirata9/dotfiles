# dotfiles

Claude Code / OpenAI Codex / GitHub Copilot / Antigravity の共通設定を管理するリポジトリ。

## 構成

```
dotfiles/
├── agent/
│   └── AGENTS.md          # 共通ルール（Single Source of Truth）
│                          #   コーディングルール、口調、Git規約など
└── claude/
    ├── CLAUDE.md          # Claude Code 専用設定（AGENTS.md を @import）
    └── settings.json      # Claude Code 設定（defaultMode, language など）
```

## セットアップ

```powershell
.\setup.ps1 -DryRun   # 確認のみ
.\setup.ps1 -Force    # 実行（既存ファイルをバックアップして上書き）
```

シンボリックリンクが作成される場所:

| 配置先 | 実体 |
|--------|------|
| `~/.claude/CLAUDE.md` | `claude/CLAUDE.md` |
| `~/.claude/settings.json` | `claude/settings.json` |
| `~/.codex/AGENTS.md` | `agent/AGENTS.md` |

> シンボリックリンクには管理者権限または Windows Developer Mode が必要。
> どちらも使えない場合はハードリンクまたはコピーにフォールバックします。

## 設定を変更する

`agent/AGENTS.md` を編集するだけで全ツールに反映される。

Claude Code 固有の設定は `claude/CLAUDE.md` の下部に追記する。

## GitHub Copilot / Antigravity（プロジェクト単位）

プロジェクトの `.github/copilot-instructions.md` や `AGENTS.md` に
`agent/AGENTS.md` の内容をコピーして使う（またはシンボリックリンクを張る）。
