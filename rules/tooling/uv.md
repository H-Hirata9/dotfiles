## Python Tooling: uv / ruff / ty

Python は **uv（パッケージ/実行）＋ ruff（lint/format）＋ ty（型チェック）** の3点セットを標準とする。
すべて Astral 製。dev 依存に入れる: `uv add --dev ruff ty`

### uv（パッケージ管理・実行）
- パッケージ追加: `uv add <package>`（`pip install` は使わない）
- パッケージ削除: `uv remove <package>`
- スクリプト実行: `uv run <script>` または `uv run python`
- 依存関係同期: `uv sync`（`pip install -r requirements.txt` は使わない）
- 新規プロジェクト: `uv init`
- テスト実行: `uv run pytest`
- 設定ファイル: `pyproject.toml`（`setup.py`・`requirements.txt` は作らない）
- ロックファイル: `uv.lock`（コミットする）
- 仮想環境は uv が管理する。手動で `venv` を作らない

### ruff（リント / フォーマット）
- リント: `uv run ruff check`（`flake8`・`pylint` は使わない）
- 自動修正: `uv run ruff check --fix`
- フォーマット: `uv run ruff format`（`black`・`isort` は使わない）
- 設定は `pyproject.toml` の `[tool.ruff]` に書く

### ty（型チェック）
- 型チェック: `uv run ty check`（`mypy`・`pyright` は使わない）
- 設定は `pyproject.toml` の `[tool.ty]` に書く
