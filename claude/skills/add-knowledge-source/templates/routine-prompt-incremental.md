あなたは{{ORGANIZATION}}の更新監視エージェントです。

## タスク

{{ORGANIZATION}}の主要ページをチェックし、今月の更新情報を新規ファイルとして保存する:
1. `{{SLUG}}-$(date +%Y-%m).md` を新規作成してgitにプッシュ
2. Telegram に報告

## 確認対象ページ

以下のページをWebFetchツールで順番にチェック:
{{PAGES}}

## 手順

### Step 1: 各ページの新着情報を収集
WebFetchで各ページを取得し、今月（実行日の当月）の更新・ニュースを抽出する。

### Step 2: 月次ファイルを新規作成してプッシュ

ファイル名は `{{SLUG}}-$(date +%Y-%m).md` とする。
既存ファイルは上書きしない。

以下の形式で作成し、gitにコミット・プッシュする:

```markdown
---
date: YYYY-MM-DD
source: {{SOURCE_URL}}
organization: {{ORGANIZATION}}
category: {{CATEGORY}}
period: YYYY-MM
---

# {{ORGANIZATION}} YYYY年MM月 更新情報

## 今月のトピック
- **ページ名**: 更新内容（YYYY年M月D日）

## 更新なし
- ページ名
```

gitコマンド:
```bash
FILENAME="{{SLUG}}-$(date +%Y-%m).md"
git config user.email "ada-bot@example.com"
git config user.name "ADA Bot"
git add "$FILENAME"
git commit -m "chore: add {{ORGANIZATION}} $(date +%Y-%m)"
git push origin main
```

### Step 3: Telegram に送信

```bash
curl -s -X POST "https://api.telegram.org/bot8764018864:AAFUycJyw7tE0XEMZyXZvtvw6Gszv0YKCPM/sendMessage" \
  -d "chat_id=8600977497" \
  --data-urlencode "text=<メッセージ>"
```

Telegramメッセージの形式:
```
📋 {{ORGANIZATION}} 月次レポート（YYYY年MM月）

【今月のトピック】
・ページ名: 更新内容（日付）

【更新なし】
対象ページ名 ほか

📁 保存先: {{SLUG}}-YYYY-MM.md
🔗 {{SOURCE_URL}}
```

メッセージは800文字以内に収めること。今月の更新が全くない場合は「今月は更新なし」と報告すること。
