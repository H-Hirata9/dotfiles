---
name: chusho-policy
description: >
  中小企業庁（中小企業政策）の最新ニュース収集・政策解説スキル。
  「中小企業庁」「中小企業政策」「補助金」「支援策」「経営革新」「事業承継」
  「ものづくり補助金」「IT導入補助金」「小規模事業者」「賃上げ支援」などの
  キーワードが出たときに必ず使う。最新情報が必要なとき、政策の概要を知りたいとき、
  補助金・税制優遇を調べたいときも積極的に使う。
---

# 中小企業庁 政策情報スキル

中小企業庁の公式サイトから最新の政策情報を収集し、わかりやすく解説するスキル。

## 情報源

メインページ: https://www.chusho.meti.go.jp/support/index.html

## 政策カテゴリとURL一覧

| カテゴリ | URL |
|---|---|
| 100億宣言 | https://www.chusho.meti.go.jp/keiei/100oku/index.html |
| 経営力向上支援 | https://www.chusho.meti.go.jp/keiei/kyoka/index.html |
| 経営革新支援 | https://www.chusho.meti.go.jp/keiei/kakushin/index.html |
| 先端設備等導入制度 | https://www.chusho.meti.go.jp/keiei/seisansei/index.html |
| 経営支援体制 | https://www.chusho.meti.go.jp/keiei/network/index.html |
| 雇用・人材支援 | https://www.chusho.meti.go.jp/keiei/koyou/index.html |
| イノベーション支援 | https://www.chusho.meti.go.jp/support/innovation/index.html |
| 事業承継 | https://www.chusho.meti.go.jp/zaimu/shoukei/index.html |
| 創業・スタートアップ支援 | https://www.chusho.meti.go.jp/keiei/chiiki/index.html |
| 海外販路開拓支援 | https://www.chusho.meti.go.jp/shogyo/chiiki/index.html |
| 事業再構築・生産性向上支援 | https://www.chusho.meti.go.jp/keiei/sapoin/index.html |
| デジタル・IT化支援 | https://www.chusho.meti.go.jp/keiei/gijut/index.html |
| 小規模企業支援 | https://www.chusho.meti.go.jp/keiei/shokibo/index.html |
| 商業活性化 | https://www.chusho.meti.go.jp/shogyo/shogyo/index.html |
| 金融一般支援 | https://www.chusho.meti.go.jp/kinyu/index.html |
| 取引適正化・価格転嫁 | https://www.chusho.meti.go.jp/keiei/torihiki/index.html |
| 経営安定支援 | https://www.chusho.meti.go.jp/keiei/antei/index.html |
| 賃上げ・最低賃金対応支援 | https://www.chusho.meti.go.jp/chingin/index.html |
| 税制 | https://www.chusho.meti.go.jp/zaimu/zeisei/index.html |
| 予算 | https://www.chusho.meti.go.jp/koukai/yosan/index.html |

## ワークフロー

### 1. 最新ニュースを収集する場合（並列Haiku Agent — 推奨）

複数カテゴリを同時収集する場合は、Haiku モデルの並列 Agent を使う。
コストを抑えつつ高速に取得できる（Sonnetの約1/4のコスト）。

```
# 以下を1つのメッセージで同時起動（run_in_background: true）
Agent(subagent_type="Explore", model="haiku", run_in_background=True, prompt="""
<カテゴリ名>のページから最新情報を取得。
お知らせ・補助金・公募期間を3〜5点箇条書きで。
URL: <対象URL>
WebFetch ツールを使って取得してください。
""")
# ← 複数カテゴリ分を同時起動

# 全エージェント完了後に結果を統合してまとめる
```

対象カテゴリは調査目的に応じて上記URL一覧から選ぶ。
広範調査なら5〜10カテゴリ、ピンポイント調査なら1〜3カテゴリ。

### 2. 特定政策の詳細を調べる場合

上記のURL一覧から該当するURLを選んでスクレイプする。
ページ内に「お知らせ」「更新情報」「新着情報」のセクションがあれば、そこを中心に読む。

```bash
npx firecrawl scrape "<対象URL>" --only-main-content -o .firecrawl/chusho-<policy>.md
```

リンク先に詳細ページや公募要領PDFが含まれている場合、内容を確認してから回答する。

### 2. 特定政策の詳細を調べる場合

上記のURL一覧から該当するURLを選んでスクレイプする。
ページ内に「お知らせ」「更新情報」「新着情報」のセクションがあれば、そこを中心に読む。

```bash
npx firecrawl scrape "<対象URL>" --only-main-content -o .firecrawl/chusho-<policy>.md
```

リンク先に詳細ページや公募要領PDFが含まれている場合、内容を確認してから回答する。

### 3. ニュース・最新動向の検索

Firecrawl の検索を活用して最新情報を補完する。

```bash
npx firecrawl search "中小企業庁 <キーワード> 2026" \
  --limit 5 -o .firecrawl/chusho-search.json --json
```

## 回答フォーマット

### 最新ニュース収集の場合

```
📋 中小企業庁 最新政策情報（YYYY-MM-DD 時点）

【カテゴリ名】
・〇〇に関する新しい補助金が公募開始（公募期間: ）
・〇〇制度の申請受付が始まっています

【カテゴリ名】
・...

🔗 詳細: https://www.chusho.meti.go.jp/...
```

### 政策解説の場合

```
📌 【政策名】

概要: （2〜3行で端的に）

対象: （対象企業・業種）
支援内容: （補助金額・税制優遇・融資条件など）
申請窓口: （どこに問い合わせるか）
注意点: （締切・要件など重要事項）

🔗 詳細: <URL>
```

## 注意事項

- 中小企業庁のサイトは定期的に更新されるため、**必ずスクレイプして最新情報を取得**してから回答する。手元の知識だけで答えない。
- 補助金の公募期間・金額は変更されることが多いので、取得した情報に日付を明記する。
- PDFリンクが多いサイトなので、HTMLページの概要を確認してから必要に応じてPDF内容を案内する。
