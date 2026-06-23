---
name: session-search
description: Claude Code の全セッション(.jsonl)を全文検索してADAの長期記憶を引く。「前に何を決めたか」「いつ〇〇の話をしたか」「過去のあの作業」を思い出すときに使う。日本語OK(trigram)。
metadata:
  category: memory
  tags: [memory, search, sqlite, fts5, recall]
---

# session-search — 全セッション全文検索（ADAの長期記憶）

## いつ使うか
- 「前に〇〇についてどう決めたっけ」「いつ△△の話をした？」「過去のあの作業/設計判断」を思い出すとき
- 手書きの引き継ぎ要約に頼らず、過去の生ログ（.jsonl）を直接引く
- ada-board #13 の実装。Hermes Agent の state.db / session_search 相当

## 使い方
```
python ~/.claude/skills/session-search/session_search.py search "<クエリ>" [--limit 8] [--since 2026-06-01]
python ~/.claude/skills/session-search/session_search.py status
python ~/.claude/skills/session-search/session_search.py index   # 通常は不要(検索時に自動増分)
```
依存は標準ライブラリのみ（uv 不要、`python` で直接実行可）。

## 仕組み（要点）
- 索引 DB: `~/.claude/ada/sessions.db`（FTS5 + **trigram** トークナイザ＝日本語/CJK 対応に必須）
- データ源: `~/.claude/projects/<slug>/<conv-id>.jsonl`。user/assistant の本文・思考・tool 呼び出しを平文化して索引
- **増分**: `ingested_files.last_byte_offset` を持ち、追記分だけ seek。検索時に自動で増分同期してから検索（on-demand）
- **検索(DISCOVERY)**: query→FTS5 MATCH→bm25 順→各ヒットに ±5 メッセージ窓＋セッション先頭/末尾3件(bookends)
- 検索のクエリ展開（同義語・日英の揺れ）は ADA 側で行う＝「バグ OR 修正 OR エラー」のように複数語を投げる。semantic 検索は不採用（#13 参照）

## 注意・落とし穴
- 3文字以上は FTS5 trigram（高速・bm25 順）。**1〜2文字（「AI」「税」等）は自動で LIKE フォールバック**（全走査だが小規模DBなので一瞬、bm25 が無いので新しい順）。短語でも黙ってゼロヒットにはならない
- 同義語は1クエリにまとまらない → ADA が言い換えて複数回投げる
- `sessions.db` は .jsonl から**再生成可能なキャッシュ**。git には commit しない（壊れたら削除して再 index）
- .jsonl スキーマは Claude Code 更新で変わりうる。空ヒットが続いたら schema を再確認（type=user/assistant, message.content）
- 任意で夜間 Task Scheduler に `index` を仕込めるが、on-demand 同期があるので必須ではない

## 関連
- 設計と agy(Pro)レビュー: ada-board #13
- コンテキスト圧縮時の長期参照口として CLAUDE.md §8 から参照される
