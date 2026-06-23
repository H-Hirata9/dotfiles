---
name: pdf-to-wiki
description: >
  PDFファイルを受け取ってwiki/raw/にテキスト抽出し、Ingestするスキル。
  「このPDFをwikiに追加して」「PDFをIngestして」「教材を取り込んで」
  などの指示があるときに使う。
---

# PDF → Wiki Ingest スキル

PDFのテキストを抽出してwiki/raw/に保存し、Ingestするワークフロー。

## 実行スクリプト

```
uv run --project $HOME/.claude/skills/pdf-to-wiki python $HOME/.claude/skills/pdf-to-wiki/scripts/pdf_extract.py "<PDFパス>" --title "<タイトル>" --source "<出典>"
```

## ワークフロー

```
[Step 1] PDFを受け取る
  - Telegram経由: download_attachment でローカルパスを取得
  - ローカルパス指定: そのまま使用

[Step 2] pdf_extract.py を実行
  - 通常のPDFならそのまま抽出
  - 制限付き暗号化PDFの場合は自動的に空パスワードで復号を試みる
  - 開くためのパスワードが必要なPDFは対応不可（エラーになる）

[Step 3] 出力ファイルを確認
  - wiki/raw/<date>_<slug>.md に保存されているか確認

[Step 4] 通常のIngestフローを実行
  - wiki/SCHEMA.md を読んで Ingest 手順に従う
  - sources / entities / concepts ページを作成
  - index.md・log.md を更新

[Step 5] Lint-on-Ingest
  - 新規ページの[[wikilink]]が全て実在するか確認
  - 問題があれば即修正

[Step 6] Telegram に完了報告
```

## 注意事項

- 「空パスワードで復号」は制限付きPDFへの対応であり、開くためのパスワードが別途かかっているPDFには使えない
- テキストではなく画像として格納されているPDFはテキスト抽出できない（別途OCRが必要）
- 著作権上、個人学習の範囲内での使用を前提とする
