---
name: add-knowledge-source
description: >
  新しい定期情報収集ルーティンを cch-bot-knowledge に追加するスキル。
  「○○の情報を定期収集したい」「新しい情報源を追加して」「毎月○○をチェックして」
  「○○のページを監視してほしい」など、新規ルーティン作成を求められたら必ずこのスキルを使う。
  既存ルーティンの変更・削除には使わない。
---

# 新規知識ソース追加スキル

`cch-bot-knowledge` リポジトリに新しい定期収集ルーティンを追加する。
RemoteTrigger を作成し、README とルーティン管理ドキュメントを更新する。

## 必要な情報を収集する

以下の情報が揃っていない場合は確認する。

| 項目 | 説明 | デフォルト |
|---|---|---|
| `ORGANIZATION` | 情報提供元の組織名 | — |
| `SLUG` | ファイル名用の識別子（英小文字・ハイフン） | 組織名からADAが生成 |
| `PAGES` | チェック対象URLと説明（複数可） | — |
| `SOURCE_URL` | 代表URL（Telegram通知に表示） | PAGES の最初のURL |
| `CATEGORY` | 情報カテゴリ（例: 政策, 補助金, 税制, 金融支援, ニュース） | — |
| `PATTERN` | `overwrite`（最新情報を上書き）または `incremental`（月次ファイルを蓄積） | `overwrite` |
| `CRON` | スケジュール（UTC 5フィールド） | `0 3 3 * *`（毎月3日 12:00 JST） |

### PATTERN の使い分け

- **overwrite**: 「常に最新の状態を1ファイルで把握したい」場合。政策・制度情報など更新頻度が低く、最新版だけあればよいもの。ファイル名は `{SLUG}-latest.md`（固定）。テンプレート: `routine-prompt-overwrite.md`
- **incremental**: 「月ごとの記録を蓄積したい」場合。ニュース・動向など時系列で振り返りたいもの。ファイル名は `{SLUG}-YYYY-MM.md`（月次生成）。テンプレート: `routine-prompt-incremental.md`
- **news-search**: WebSearch で複数組織のニュースを日次収集する場合。`PAGES` の代わりに `TOPICS`（組織名リスト）と `SEARCH_QUERIES`（検索クエリリスト）を使う。ファイル名は `{SLUG}-YYYY-MM-DD.md`（日次生成）。allowed_tools に `WebSearch` を追加する。テンプレート: `routine-prompt-news-search.md`

## 承認要求を出す

情報が揃ったら、実行前に必ず承認を求める。

```
【承認要求】
操作: RemoteTrigger を新規作成
理由: {{ORGANIZATION}} の定期収集ルーティンを追加
副作用:
  - RemoteTrigger 作成（毎月実行、課金が発生）
  - cch-bot-knowledge/README.md に行を追加
  - Vault/telegram_cch_bot/ルーティン管理.md に行を追加
パターン: {{PATTERN}}（{{上書き or 月次蓄積}}）
スケジュール: {{CRON}}（次回実行: YYYY年MM月DD日）
出力ファイル: {{overwriteなら {SLUG}-latest.md、incrementalなら {SLUG}-YYYY-MM.md}}

実行してよいですか？ (yes で実行 / no でキャンセル)
```

## ルーティンを作成する

承認後、以下の順序で実行する。

### Step 1: テンプレートを選択して読み込む

`PATTERN` に応じてテンプレートを選択する:

- `overwrite` → `templates/routine-prompt-overwrite.md` を Read
- `incremental` → `templates/routine-prompt-incremental.md` を Read

以下のプレースホルダーを置換する:

| プレースホルダー | 置換内容 |
|---|---|
| `{{ORGANIZATION}}` | 組織名 |
| `{{SLUG}}` | ファイル名識別子 |
| `{{PAGES}}` | 番号付きURLリスト（例: `1. https://... （説明）`） |
| `{{SOURCE_URL}}` | 代表URL |
| `{{CATEGORY}}` | カテゴリ |
| `{{FILENAME}}` | overwrite時のみ: `{SLUG}-latest.md` |

### Step 2: RemoteTrigger を作成する

```json
{
  "name": "{{ORGANIZATION}} 更新チェック",
  "cron_expression": "{{CRON}}",
  "job_config": {
    "ccr": {
      "environment_id": "env_011CUMMXxtDsf2kUaioVKQXM",
      "events": [{ "data": { "message": { "content": "<置換済みプロンプト>", "role": "user" } }, "type": "user" }],
      "session_context": {
        "allowed_tools": ["Bash", "Read", "Write", "WebFetch"],
        "model": "claude-sonnet-4-6",
        "sources": [{ "git_repository": { "url": "https://github.com/H-Hirata9/cch-bot-knowledge" } }]
      }
    }
  }
}
```

### Step 3: cch-bot-knowledge/README.md を更新する

`$HOME/projects/life/cch-bot-knowledge/README.md` の「現在の知識ファイル」テーブルに1行追加する。

- overwrite: `| \`{SLUG}-latest.md\` | {{ORGANIZATION}} | {{CATEGORY}} | {{頻度}} |`
- incremental: `| \`{SLUG}-*.md\` | {{ORGANIZATION}} | {{CATEGORY}} | {{頻度}}（月次蓄積） |`

### Step 4: ルーティン管理.md を更新する

`$HOME/Vault/telegram_cch_bot/ルーティン管理.md` に新しいルーティンのセクションを追加する。

```markdown
### {{ORGANIZATION}} 更新チェック

| 項目 | 内容 |
|---|---|
| **ID** | `<作成されたtrigger_id>` |
| **パターン** | {{overwrite: 上書き / incremental: 月次蓄積}} |
| **スケジュール** | {{頻度の日本語表現}} |
| **cron (UTC)** | `{{CRON}}` |
| **ステータス** | 有効 |
| **次回実行** | {{次回実行日時 JST}} |
```

### Step 5: 完了を報告する

```
✅ {{ORGANIZATION}} 更新チェック ルーティンを作成したよ

📌 実施内容:
- RemoteTrigger ID: <id>
- パターン: {{overwrite or incremental}}
- スケジュール: {{頻度の日本語表現}}
- 出力ファイル: {{ファイル名パターン}}

📁 更新ファイル:
- cch-bot-knowledge/README.md
- Vault/telegram_cch_bot/ルーティン管理.md
```
