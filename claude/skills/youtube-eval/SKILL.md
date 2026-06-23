---
name: youtube-eval
description: >
  YouTube動画のURLを受け取って字幕を取得し、ADAが内容を評価・解説するスキル。
  「この動画を見て」「YouTube動画を解説して」「動画を評価して」
  などの指示があるときに使う。
---

# YouTube 動画評価スキル

YouTube動画の字幕・メタデータを取得してADAが日本語で解説・評価する。

## 実行スクリプト

```
uv run --project ~/.claude/skills/youtube-eval python ~/.claude/skills/youtube-eval/scripts/eval.py "<YouTube URL>"
```

## ワークフロー

```
[Step 1] URLからスクリプトを実行
  - 字幕取得: 日本語 → 英語 → 自動生成の順で試みる
  - メタデータ (タイトル・チャンネル名) も取得

[Step 2] 出力を読んで ADA が日本語で解説
  - タイトル・チャンネル・URL を冒頭に記載
  - 内容の要約（主要なポイントを箇条書き）
  - 有益な知見・学び
  - 懸念点・注意点（あれば）

[Step 3] 必要に応じて wiki に Ingest
  - 「ingestして」と指示があれば wiki/raw/ に保存してフロー継続
  - sources/ ページを作成し、concepts/ に関連概念を追加
```

## 注意事項

- 字幕がない動画や字幕が無効化されている動画は内容取得不可
- 字幕が8000文字を超える場合は先頭部分のみ使用（省略あり）
- 取得した字幕は自動生成の場合、誤認識が含まれることがある
