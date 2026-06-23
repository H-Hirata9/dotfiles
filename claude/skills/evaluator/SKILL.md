---
name: evaluator
description: ADA自身の出力品質を月次で評価するループ。誤報・手戻り・承認逸脱・自己訂正・ツール空振りを既存ログから集計し、ダッシュボード用JSON＋人間向けMDレポートを出力する。「品質評価して」「今月の評価レポート作って」「ADAの振り返りして」等で使う。月次の棚卸し時に回す。
metadata:
  category: ops
  tags: [evaluation, quality, monitoring, dashboard, ada]
---

# evaluator — ADA品質評価ループ（⑲Evaluation）

`Agentic Design Patterns`(A.Gulli) の ⑲Evaluation & Monitoring を埋めるツール。
ADAの出力品質を月次で測り、繰り返しミスを検知して学習(#23/⑨)へ流す。
設計の正本: ada-board #21 / 計画 `$HOME/.claude/plans/2026-06-23_ada-board-21_quality-eval-loop.md`

## いつ使うか
- 月次の棚卸し時、または主人が「品質評価して」と言ったとき
- 出力を見て主人レビュー → 繰り返しパターンを Reflexion で汎用ルール化 → feedbackメモリへ

## 使い方
```
# プレビュー（書き込みなし。stdout にMDレポート）
uv run --project $HOME/.claude/skills/evaluator python $HOME/.claude/skills/evaluator/scripts/eval_collect.py --month 2026-06 --no-gh

# 本番（cch-bot-knowledge/eval/ に JSON+MD 出力。gh で reopened issue も集計）
uv run --project $HOME/.claude/skills/evaluator python $HOME/.claude/skills/evaluator/scripts/eval_collect.py --month 2026-06 --write
```
- `--month YYYY-MM`: 対象月（既定=今月）
- `--write`: `cch-bot-knowledge/eval/eval-YYYY-MM.{json,md}` に出力
- `--no-gh`: gh 呼び出しをスキップ（オフライン/テスト時）

## 出力（2層構造）
- **層1 データ**: `eval-YYYY-MM.json` … 固定スキーマの時系列。ダッシュボードの正本（キー追加は後方互換で）
- **層2 レポート**: `eval-YYYY-MM.md` … JSONから生成。frontmatter＋表。Obsidian/Telegramで読める

スキーマ: `baseline{total_tasks, avg_tool_steps, completion_rate}` /
`metrics{factual_error, rework, policy_violation, self_correction, tool_spin}` /
`repeated_patterns[]` / `events[]`

## シグナル源と検知方針（Gemini Proレビュー反映）
- **システムイベント主軸**でノイズを抑える: 連続ツール失敗=tool_spin、ada-guard.log の BLOCK=policy_violation、reopened issue=rework
- 人間の割り込み（短い「違う/ストップ」等）=rework。**長文・注入テキストは弾く**（偽陽性対策）
- 自己訂正（assistant の「撤回/誤報/訂正」）=self_correction（健全な兆候）
- **誤報(factual_error)は自動検知しない**。主人の月次レビューで最終ラベルを付ける（HITL維持）

## レビュー後のフロー（Phase 2 / #23 連動）
繰り返しパターンを feedback メモリに登録する前に、ADA自身に
「このミスを未然に防ぐ汎用ルール(Contextual Rule)を1〜2行で書け」と**Reflexion**させてから登録する。
例: ×「〇〇を間違えた」→ ○「〇〇を操作する時は事前に△△を確認する」

## 制約・既知の限界
- キーワード系シグナル（rework/self_correction）は偽陽性が残る。**生カウントは目安**、確定は人間
- `completion_rate` は客観シグナル未確立のため null（捏造しない）
- 依存は標準ライブラリのみ。`uv run --project` で実行

## テスト
```
uv run --project $HOME/.claude/skills/evaluator --dev pytest $HOME/.claude/skills/evaluator/tests/ -q
```
