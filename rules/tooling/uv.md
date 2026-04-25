## Python Tooling: uv

- パッケージ追加: `uv add <package>`（`pip install` は使わない）
- パッケージ削除: `uv remove <package>`
- スクリプト実行: `uv run <script>` または `uv run python`
- 依存関係同期: `uv sync`（`pip install -r requirements.txt` は使わない）
- 新規プロジェクト: `uv init`
- テスト実行: `uv run pytest`
- 設定ファイル: `pyproject.toml`（`setup.py`・`requirements.txt` は作らない）
- ロックファイル: `uv.lock`（コミットする）
- 仮想環境は uv が管理する。手動で `venv` を作らない
