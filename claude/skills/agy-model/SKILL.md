---
name: agy-model
description: agy(Antigravity CLI)の使用モデルを用途別に切り替える。設計/アーキ相談の前に pro、要約・抽出・画像生成は flash。agy/antigravity_ask を呼ぶ前にモデルを合わせるときに使う。
metadata:
  category: tooling
  tags: [agy, antigravity, model, routing]
---

# agy-model — agy のモデル用途別ルーティング

## いつ使うか
`antigravity_ask` / `antigravity_image` 等で agy を呼ぶ**前**に、タスクに合うモデルへ切り替える。

- **pro**（Gemini 3.1 Pro (High)）: 設計レビュー・アーキ相談・難しい技術判断の壁打ち
- **flash**（Gemini 3.5 Flash (High)）: 要約・抽出・分類・画像生成など軽量で速い作業
- **既定は flash**。pro に上げたら、重い相談が終わったら flash に戻す

## なぜ settings.json 方式か
agy の MCP ブリッジは headless `agy -p` を使う。`-p` に `--model` を渡すと**ハングする**（1.0.9で実証）。
そのため使用モデルは `~/.gemini/antigravity-cli/settings.json` の `"model"` フィールドで制御する。
このスクリプトがその欄を安全に書き換える（書換前に .bak を作成、tmp→replace でアトミック）。

## 使い方
```
python ~/.claude/skills/agy-model/set_model.py status
python ~/.claude/skills/agy-model/set_model.py list
python ~/.claude/skills/agy-model/set_model.py pro
python ~/.claude/skills/agy-model/set_model.py flash
python ~/.claude/skills/agy-model/set_model.py set "Gemini 4 Pro (High)"
```
依存は標準ライブラリのみ（uv 不要、`python` で直接実行可）。

## モデル一覧・バージョンアップ追従
- モデル一覧とプリセットは `agy_models.json` に持つ（`set_model.py` が読む）。
- `agy models` のライブ一覧はスクリプトから捕捉できない（ConPTY 直書き／winpty も headless で失敗）。一覧の正は **公式**:
  - Codelab（正確な文字列入り）: https://codelabs.developers.google.com/antigravity-cli-hands-on
  - 公式docs: https://antigravity.google/docs
- **追従手順（モデルが版上げ/改名されて agy 呼び出しが失敗したとき）**:
  1. 上の公式ページを WebFetch して現行のモデル名一覧を取得
  2. `agy_models.json` の `available` と `presets`（pro/flash）を新しい文字列に更新、`updated` を当日に
  3. `set_model.py status` で確認して再実行
- 既知一覧にない文字列を指定しても `set` で適用は可能（warn を出すだけ）。誤りなら次の agy 呼び出しでハング/エラーとして顕在化する。

## 典型フロー
1. `set_model.py pro` → `antigravity_ask`（設計レビュー）→ 必要なら `set_model.py flash` に戻す
2. 画像生成や要約は `set_model.py flash` を確認してから `antigravity_image` 等

## 落とし穴
- 切替は agy の**永続設定**を変える（次回以降の全 agy 呼び出しに影響）。用途が変わったら明示的に戻す
- モデル文字列は agy が受け付ける正確な表記である必要がある（presets に固定済み）
- 関連: agy 導入経緯=ada-board #12 / 画像生成の使い方=memory feedback_image_gen_agy
