# routines — ADA 定期タスクの宣言的管理

`routines.toml` が ADA の定期タスク（Windows: Task Scheduler / Linux: systemd user timer）の**正本**。
2026-07-11 導入。それ以前は Task Scheduler の GUI 内にしか定義が存在せず、マシン移行のたびに手作業だった。

## 使い方

```sh
# ドリフト検知（読み取り専用・既定）: マニフェスト vs 現環境
python scripts/routines.py check

# 登録内容のプレビュー（dry-run。書き込みなし）
python scripts/routines.py install

# 実登録（Windows: schtasks / Linux: ~/.config/systemd/user へ unit 生成）
python scripts/routines.py install --apply   # ← ADA が打つ場合は事前承認必須

# 現環境の Task Scheduler から TOML 雛形を出力（新タスクの取り込み用）
python scripts/routines.py export
```

## 設計メモ
- ツールの絶対パス（dotenvx / uv / python / pwsh）はマニフェストに書かない。実行時に `which` / `Get-Command` で解決する
  （旧: winget の長い絶対パスがタスク定義に直書きされていて移行不能だった）
- `venv-python` は `<workdir>/.venv` の python（Windows: Scripts\python.exe / Linux: bin/python）
- schedule は cron 風 5 フィールドだが対応は daily / weekly / monthly のみ。曜日は 0=日曜
- 定期タスクの新規追加・変更は CLAUDE.md §12 により承認必須。`check` と dry-run は自由
- Linux 側 unit は `--out` で出力先変更可（検証用）。タイマーは `Persistent=true`（起動時に取りこぼし実行）

## テスト

```sh
uv run --with pytest pytest tests/ -q
```
