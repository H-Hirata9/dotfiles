---
name: obsidian-vault
description: Obsidian Vault（C:\Users\nov26\Vault\）の読み書き権限ルールと、wiki（LLMwikiスタイル）のIngest/Lint/Query手順。Vault配下のファイルを読み書きするとき、特に「wikiに追加して」「raw/の〇〇をIngestして」「wikiをLintして」「研究結果をVaultに保存」等の指示で着手前に読む。
---

# obsidian-vault — Vault 管理ルール

Obsidian は **主人が読む成果物の置き場**。ADA の内部記憶（`~/.claude/ada/`）とは役割が違う。

## ディレクトリ別の ADA 権限
| ディレクトリ | 読み | 書き |
|---|---|---|
| `daily_notes/` | ✗ 禁止 | ✗ 禁止（別ボット管理） |
| `study/` | ✗ 禁止 | ✗ 禁止（診断士対策） |
| `creative/` | 創作系の話題のときのみ | ✗ 禁止 |
| `research/` | ○ | ○ ADAの出力先（単発ダンプ） |
| `wiki/` | ○ | ○ 更新・追記・新規作成すべて可 |
| `telegram_cch_bot/` | ○ | ○ プロジェクト管理用 |
| `ada_worklog/` | ○ | ○ worklog skill が追記（直接編集しない） |

## research/ への出力ルール
- ファイル名: `YYYY-MM-DD_<タイトル>.md` / YAML frontmatter にタグ必須
- 既存ノートの**上書き禁止**（新規作成のみ）
- ADA 自身のメモ・サマリーは**ここに書かない**（`~/.claude/ada/` へ）

## wiki/ 管理（LLMwiki スタイル）
ルールは `Vault/wiki/SCHEMA.md` に定義。**作業前に必ず Read**。専門の wiki-worker サブエージェントに委譲してもよい。

- **Ingest**（「〇〇をwikiに追加」「raw/の〇〇をIngest」）→ SCHEMA.md の手順で sources/entities/concepts を作成・更新 → index.md と log.md を必ず更新
- **Lint**（「wikiをLintして」）→ 矛盾・孤立ページ・リンク切れ・古い情報をチェックして Telegram に報告
- **Query**（「wikiから〇〇教えて」）→ index.md を起点に関連ページを読んで回答

### wiki Lint-on-Ingest（Ingest後に自動実行・完了報告の前に必ず）
1. 新規・更新ページ内の `[[wikilink]]` が実在ファイルに対応するか確認。無ければそのページを作成してから完了
2. `index.md` が更新されているか確認
3. `log.md` に追記されているか確認
