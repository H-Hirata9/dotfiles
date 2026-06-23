---
name: nature-remo
description: Nature Remo 経由で自宅エアコンを ON/OFF・状態確認する。「エアコンつけて」「冷房26度にして」「エアコン消して」「エアコンの状態は？」等で使う。実体は projects/life/nature_remo/ac.py。
metadata:
  category: home
  tags: [nature-remo, aircon, iot, home]
---

# nature-remo — エアコン操作

Nature Remo 経由で自宅のエアコンを操作する。実体は `$HOME/projects/life/nature_remo/ac.py`。
秘密(トークン)は dotenvx で暗号化管理（[[dotenvx]] スキル）。

## 使い方（nature_remo ディレクトリで dotenvx run 経由）
```
cd $HOME/projects/life/nature_remo
dotenvx run -- uv run python ac.py status
dotenvx run -- uv run python ac.py on [--temp 26] [--mode cool]
dotenvx run -- uv run python ac.py off
```
- `status`: 現在の運転状態
- `on`: 電源ON（`--temp` 温度 / `--mode cool|warm|dry` 等）
- `off`: 電源OFF

## 注意
- 必ず `dotenvx run --` 経由で呼ぶ。dotenvx 無しの直起動は KeyError で安全停止（暗号文字列を外部に投げない設計。[[dotenvx]]）
- トークンは .env.keys（ローカル・gitignore）＋ Bitwarden 控え。新端末復旧は dotenvx スキルの手順
