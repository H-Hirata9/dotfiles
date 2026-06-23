---
name: dotenvx
description: プロジェクトの秘密(.env)を dotenvx で暗号化管理し、ポータブルにする運用規約と手順。「.envをdotenvx化して」「秘密をdotenvxに移行」「新規プロジェクトの秘密管理」「dotenvxで暗号化」等で使う。既存プロジェクトの移行・新規プロジェクトの初期設定・鍵管理・push設定を一貫してカバー。
metadata:
  category: security
  tags: [dotenvx, secrets, env, portability, bitwarden]
---

# dotenvx — プロジェクト秘密管理＆ポータビリティ

ADAの秘密管理の標準は **dotenvx**。.env を暗号化してコミット可能にし、新端末でも復元できる状態にする。
背景・計画: `~/.claude/plans/2026-06-23_dotenvx-migration.md`。#24ポータビリティと連動。

## 運用モデル（確定方針）
- **暗号化 .env はコミットする**（公開鍵＋`encrypted:`値。構成管理＆ポータビリティ）
- **秘密鍵 .env.keys はローカルのみ**（gitignore）＋ **Bitwarden に控え**
- **load_dotenv は撤去**し `dotenvx run` 経由で起動（直起動は KeyError で安全停止＝暗号文字列を外部に投げない）
- per-project キー（1個漏れても他は無事）

## 鍵の保管（Bitwarden）
1アイテム「dotenvx private keys」（セキュアノート）＋プロジェクト別の**隠しカスタムフィールド**:
`nature_remo` → `<DOTENV_PRIVATE_KEYの値>`（type=hidden）。新端末復旧時はここから各 `.env.keys` を再生成。
※秘密鍵の値はチャット/ログ/メモリに**絶対出さない**。ファイルから直接Bitwardenへコピー。

## gitignore（防御の二重化）
- グローバル（dotfiles/config/git/ignore）: `.env.keys` / `.env*.keys` / `*.plain.bak` を無視（全リポ共通の安全網）
- 各リポの .gitignore: `.env`（暗号化済）の無視を**外す**＋ `.env.keys`/`*.plain.bak` を明示無視

## 既存プロジェクトの移行手順
前提: 新シェルで `dotenvx --version`（PATHはwinget導入で通る。古いセッションは要再起動 or フルパス）。
1. `cp .env .env.plain.bak`（控え）
2. `dotenvx encrypt`（値が `encrypted:` に、`.env.keys` 生成）
3. `.env.keys` の `DOTENV_PRIVATE_KEY` 値を Bitwarden（隠しフィールド）へ保管
4. スクリプトから `from dotenv import load_dotenv` と `load_dotenv(...)` を削除
5. ローカル .gitignore を更新（`.env` 無視を外し、`.env.keys`/`*.plain.bak` を明示無視）
6. 検証: 成功系 `cd <proj> && dotenvx run -- uv run python <script>` が動く／安全失敗 `uv run python <script>`（dotenvx無し）が KeyError で即停止
7. 過去履歴に平文 .env が無いか: `git log --all --oneline -- .env`（空ならクリーン）
8. コミット: `git add .env <script> .gitignore && git commit -m "chore: migrate secrets to dotenvx"`
   - **gitleaks注意**: 暗号化値/公開鍵が高エントロピーで誤検知されうる。ブロックされたら `.gitleaksignore` に該当パス追加で通す

## ポータビリティ（push先の確保）← 移行とセット
暗号化 .env をクラウドに置くと新端末で復元できる。リモートが無ければ作る:
```
gh repo create <name> --private --source . --push
```
（プライベート必須。鍵はBitwardenにあるので暗号化.envが漏れても復号されない）
ローカル限定で良ければ push 省略可。

## 新規プロジェクト
最初から dotenvx で始める: `.env` 作成 → `dotenvx encrypt` → 鍵をBitwarden → 起動は `dotenvx run --`。

## ADA の起動規約
移行済みのツールは必ず `cd <proj> && dotenvx run -- <従来コマンド>` で呼ぶ。CLAUDE.md等のコマンド例も同形に更新。

## 対象外（触らない）
- ADA通信系 `~/.claude/channels/telegram/.env`（ADAの生命線。暗号化するとTelegram通知が止まる）

## ロールバック
`cp .env.plain.bak .env && rm .env.keys` ＋ スクリプトの load_dotenv を戻す → 平文運用に復帰。

## 進捗（移行済み）
- nature_remo: 移行済み（2026-06-23 pilot）
- 残り: tts_app / daily-briefing / spotify-organizer / manga-prompt-generator / telegram_cch_bot(project側.env)
