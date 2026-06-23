---
name: worklog
description: Record a completed task into the owner's human-readable work log (Vault/ada_worklog/YYYY-MM-DD.md) and mirror it to Google Drive. Use this whenever ADA finishes a task the owner requested that involved development, file/system changes, deployments, or external operations — append a log entry right after reporting completion on Telegram. Do NOT log pure questions, casual chat, or one-off research dumps (those go to Vault/research/). This is the owner's chronological "what did ADA do for me" record.
---

# worklog — 作業ログ

主人が依頼した「**開発・変更・デプロイ・外部操作を伴うタスク**」が完了したとき、人間が読める
時系列ログに1エントリ追記し、Google Drive にミラーする。完了報告を Telegram に出した直後に呼ぶ。

**対象外**: 質問への回答・相談・雑談・単発リサーチ（リサーチは `Vault/research/` へ）。
これらは worklog に書かない。worklog は「いつ・何を頼まれ・何をやったか」の記録であって、
会話ログではない。

## 二層構成
- 正本（主人が読む）: `~/Vault/ada_worklog/YYYY-MM-DD.md`（**日次**・追記専用・Obsidian。
  日報スタイルで1日1ファイル。同じ日の複数タスクは同じファイルに追記する）
- バックアップ: Google Drive フォルダ `ada_worklog` に **Googleドキュメント**（名前=`YYYY-MM-DD`）として
  ミラー。md→HTML変換してアップロードし、Drive側で整形済みドキュメントに変換される
  （iPhoneのDrive/Docsアプリでネイティブに読めるようにするため。`.md` はiOS Driveで開けない）

## ポインタ主義（重要）
1エントリは「いつ・何を依頼され・何をやったか・成果物リンク」だけを書く。状態（今どうか）は
複製しない。commitハッシュ・ada-board番号・ファイルパスを**リンク**するに留める。詳細はそちらが
正本。worklog は時系列インデックス、ada-board は状態の正本、handover は決定の物語 — 役割を重ねない。

## 使い方

```
uv run --project ~/.claude/skills/worklog \
  python ~/.claude/skills/worklog/scripts/worklog.py \
  --title "discord_mybot ニュース刷新" \
  --request "要約改善・保存先整理・クリップ・自動削除" \
  --did "TZ修正/3点箇条書き/news-auto化/Discordクリップ/14日retention。TDD全46緑・Azureデプロイ成功" \
  --artifacts "discord_mybot 290c4d6 / cch-bot-knowledge 703fa8c / ada-board #18"
```

- `--artifacts` は任意（無ければ成果物行を省く）
- `--at <ISO8601>` で時刻指定（省略時は現在JST）
- `--no-drive` でDriveミラーを省く（オフライン時・テスト時のみ）

実行すると Vault の当日 `.md` に追記し、Drive の Googleドキュメント `ada_worklog/YYYY-MM-DD` を
update-or-create で同期する（冪等。既存ドキュメントがあれば本文を差し替える）。

## 書き方の指針
- `--title`: 短いタスク名（リポ名＋何をしたか）
- `--request`: 主人が何を頼んだか（依頼の要旨）
- `--did`: 何をやって何が起きたか（結果・テスト/デプロイ可否まで）。誇張しない、失敗は失敗と書く
- `--artifacts`: commit・Issue・PR・主要ファイル。後から辿れるように

複数の独立タスクを終えたら、まとめず1タスク1エントリで追記する。
