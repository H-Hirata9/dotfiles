"""
agy-model / set_model.py
目的: agy(Antigravity CLI)の使用モデルを用途別に切り替える（settings.jsonのmodel欄を書換）
作成: ADA (Claude Code)
承認日: 2026-06-19

背景:
- agy の MCP ブリッジ(antigravity-intern)は headless `agy -p` を使う
- `-p` に `--model` を渡すとハングするため（1.0.9で実証済み）、モデルは
  ~/.gemini/antigravity-cli/settings.json の "model" フィールドで制御する
- 用途別 routing: 設計/アーキ相談=pro / 要約・抽出・画像=flash（既定はflash）

バージョンアップ追従:
- `agy models` の一覧はスクリプトから捕捉できない（ConPTY直書き）。
- 代わりにモデル一覧/プリセットは agy_models.json に持つ。新モデルが出たら
  公式docs（agy_models.json の docs_url）を見て JSON を更新する。
- どの文字列でも `set "<name>"` で直接指定できる（新モデルへ即追従）。
- 誤った文字列を入れても次の agy 呼び出しでハング/エラーとして顕在化する。

使い方:
    python set_model.py status            # 現在のモデルを表示
    python set_model.py list              # 既知の一覧（agy_models.json）と公式URLを表示
    python set_model.py pro               # 設計レビュー用 (presets.pro)
    python set_model.py flash             # 軽量・画像用 (presets.flash)
    python set_model.py set "Gemini 4 Pro (High)"   # 任意の文字列を直接指定
"""

import json
import os
import sys

SETTINGS_PATH = os.path.join(
    os.path.expanduser("~"), ".gemini", "antigravity-cli", "settings.json"
)
MODELS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agy_models.json")


def load_models_config() -> dict:
    with open(MODELS_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_settings() -> dict:
    if not os.path.isfile(SETTINGS_PATH):
        raise FileNotFoundError(f"settings.json が見つからない: {SETTINGS_PATH}")
    with open(SETTINGS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_settings(data: dict) -> None:
    backup = SETTINGS_PATH + ".bak"
    if os.path.isfile(SETTINGS_PATH):
        with open(SETTINGS_PATH, encoding="utf-8") as src, open(
            backup, "w", encoding="utf-8"
        ) as dst:
            dst.write(src.read())
    tmp = SETTINGS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SETTINGS_PATH)


def apply_model(target: str, cfg: dict) -> int:
    settings = load_settings()
    current = settings.get("model", "(未設定)")
    available = cfg.get("available", [])
    if target not in available:
        print(f"[warn] '{target}' は既知の一覧にない（バージョンアップ?）。")
        print(f"       公式で確認: {cfg.get('docs_url')}")
        print("       問題なければそのまま適用する（誤りなら次のagy呼び出しで顕在化）。")
    if current == target:
        print(f"already set: {target}")
        return 0
    settings["model"] = target
    save_settings(settings)
    print(f"model changed: {current} -> {target}")
    return 0


def main(argv: list[str]) -> int:
    cfg = load_models_config()
    presets = cfg.get("presets", {})

    if len(argv) == 2 and argv[1] == "status":
        settings = load_settings()
        print(f"current model: {settings.get('model', '(未設定)')}")
        print("presets:")
        for k, v in presets.items():
            print(f"  {k:5s} -> {v}")
        return 0

    if len(argv) == 2 and argv[1] == "list":
        print(f"known models (agy_models.json, updated {cfg.get('updated')}):")
        for m in cfg.get("available", []):
            print(f"  - {m}")
        print(f"presets: {presets}")
        print(f"official list: {cfg.get('docs_url')}")
        print("live source (端末でのみ表示可): agy models")
        return 0

    if len(argv) == 2 and argv[1] in presets:
        return apply_model(presets[argv[1]], cfg)

    if len(argv) == 3 and argv[1] == "set":
        return apply_model(argv[2], cfg)

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
