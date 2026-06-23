---
name: python-tool-dev
description: ADAがPythonツール/スクリプトを設計・実装するときの開発フロー（設計→承認→TDD→実装→報告）とコーディング規約。新しい.pyの作成・既存ツールの改修・パッケージ追加など、Python開発に着手する前に読む。「ツール作って」「スクリプト書いて」「〇〇を自動化して」等の開発依頼で使う。
---

# python-tool-dev — Python ツール開発フロー

ADA が Python ツール/スクリプトを作る・直すときの作法。着手前にこれに従う。

## 原則: 設計→承認→テスト作成→実装→報告（TDD デフォルト）

> 主人の特別な許可がない限り、デフォルトでテスト駆動開発（TDD）を行う。
> 失敗するテストを先に書き、それを通す最小実装を書く（Red→Green→Refactor）。
> テストを省略・後回しにしてよいのは主人が明示的に許可した場合のみ。

```
[Step 1] 要件定義
  ├─ 目的・入出力・依存ライブラリを明文化
  └─ 既存ツールで代替できないか確認

[Step 2] 設計を Telegram に提示 → 承認待ち  ← 必須（新規ツール開発はHITL対象）
  ├─ ファイルパス / 関数シグネチャ
  ├─ 副作用（ファイル書き込み・API呼び出し等）
  └─ 「承認しますか？ (yes/no)」で確認

[Step 3] テスト作成（先・TDD）
  ├─ 失敗するユニットテストを先に書く（Red）
  └─ 期待する入出力・境界条件を明文化

[Step 4] 実装
  ├─ テストを通す最小実装（Green）→ 必要ならリファクタ
  └─ `uv run pytest` で全テスト緑を確認

[Step 5] 報告
  └─ 作成ファイル一覧・テスト結果を Telegram に返信（worklog skill で作業ログも）
```

## 既存ツール群の活用優先度
1. 既存スキル (`$HOME/.claude/skills/`) を再利用
2. 既存プロジェクト内のモジュールを再利用
3. 標準ライブラリ
4. 既存 venv の依存パッケージ
5. 新規パッケージ（`uv add` — **承認必須**）

## スキル化原則
ADA のルーティン作業を効率化するツール・スクリプトは、原則として SKILL として作成する。
```
$HOME/.claude/skills/<skill-name>/
├── SKILL.md          ← スキル定義・使い方
├── pyproject.toml    ← uv プロジェクト（依存を閉じて管理）
├── uv.lock
└── scripts/<script>.py
```
- 実行: `uv run --project $HOME/.claude/skills/<skill-name> python $HOME/.claude/skills/<skill-name>/scripts/<script>.py`
- 特定プロジェクト専用でない限り、外部プロジェクトにスクリプトを混在させない

## コーディング規約（詳細は rules/coding.md と統合）
- 型ヒントを必ず使う。設定は環境変数から（ハードコード禁止）。エラーは境界で扱い握りつぶさない。
- 変更は最小限。既存スタイルを尊重。不要な抽象化・将来への備えをしない。コメントは原則書かない（理由が非自明な時だけ1行）。

```python
"""<モジュール名> / 目的: <一行> / 作成: ADA (Claude Code) / 承認日: <YYYY-MM-DD>"""
import logging, os
logger = logging.getLogger(__name__)
API_KEY = os.environ["SERVICE_API_KEY"]  # ハードコード禁止

def fetch_data(url: str, timeout: int = 30) -> dict:  # 型ヒント必須
    ...

try:
    result = risky_operation()
except SpecificError as e:
    logger.error("操作失敗: %s", e)   # 握りつぶさない
    raise
```
