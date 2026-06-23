---
name: tts
description: Azure AI Speech を使ってテキストを音声合成する。日本語・英語に対応し、高品質 DragonHD ボイスも選択可能。テキスト読み上げ、WAV ファイル保存、スクリプトからのバッチ生成が必要な場合に使用する。「音声化して」「読み上げて」「WAVに変換して」「ナレーション生成」などのリクエストに対応する。
when_to_use: |
  - ユーザーがテキストを音声に変換したいとき
  - ドキュメント・スクリプト・コメントを音声ファイルにしたいとき
  - WAV ファイルとして保存したいとき
  - 複数行テキストをバッチで音声生成したいとき
  - ボイスやイントネーションを確認したいとき
disable-model-invocation: true
allowed-tools: Bash($HOME/projects/dev/tts_app/.venv/Scripts/tts.exe *)
argument-hint: "[テキスト] または [--language ja|en] [--voice VOICE_ID] [テキスト]"
---

# tts スキル

Azure AI Speech CLI (`tts`) を使ってテキストを音声合成する。

## 実行方法

`$HOME/projects/dev/tts_app/.venv/Scripts/tts.exe` を直接使う。

```bash
TTS="$HOME/projects/dev/tts_app/.venv/Scripts/tts.exe"
```

## 基本パターン

### 即時再生（ファイル保存なし）

```bash
# 日本語（デフォルトボイス: Nanami）
$HOME/projects/dev/tts_app/.venv/Scripts/tts.exe --language ja "読み上げたいテキスト"

# 英語（デフォルトボイス: Jenny）
$HOME/projects/dev/tts_app/.venv/Scripts/tts.exe --language en "Text to be read aloud"
```

### WAV ファイルに保存

```bash
$HOME/projects/dev/tts_app/.venv/Scripts/tts.exe --language ja --output output/result.wav "読み上げたいテキスト"
```

### ボイスを指定

```bash
# 高品質 HD ボイス（推奨）
$HOME/projects/dev/tts_app/.venv/Scripts/tts.exe --language ja --voice "ja-JP-Nanami:DragonHDLatestNeural" "テキスト"
$HOME/projects/dev/tts_app/.venv/Scripts/tts.exe --language ja --voice "ja-JP-Masaru:DragonHDLatestNeural" "テキスト"

# 標準ボイス
$HOME/projects/dev/tts_app/.venv/Scripts/tts.exe --language ja --voice "ja-JP-KeitaNeural" "テキスト"
```

### バッチ生成（テキストファイルから）

```bash
# script.txt の各行を個別 WAV に変換
# 出力: output/batch/01.wav, 02.wav, ...
$HOME/projects/dev/tts_app/.venv/Scripts/tts.exe --language ja --input-file script.txt --output output/batch/
```

`--input-file` の注意事項：
- 空行は自動スキップ
- 出力ファイル名は連番（`01.wav`, `02.wav`, ...）
- `--output` はディレクトリパスで指定すること（ファイルパスではない）

## 利用可能なボイス一覧

### 日本語

| ボイス ID | 説明 | 品質 |
|-----------|------|------|
| `ja-JP-NanamiNeural` | Nanami（女性） | 標準 |
| `ja-JP-KeitaNeural` | Keita（男性） | 標準 |
| `ja-JP-AoiNeural` | Aoi（女性） | 標準 |
| `ja-JP-DaichiNeural` | Daichi（男性） | 標準 |
| `ja-JP-MayuNeural` | Mayu（女性） | 標準 |
| `ja-JP-ShioriNeural` | Shiori（女性） | 標準 |
| `ja-JP-NaokiNeural` | Naoki（男性） | 標準 |
| `ja-JP-Nanami:DragonHDLatestNeural` | Nanami HD（女性） | ★高品質 |
| `ja-JP-Masaru:DragonHDLatestNeural` | Masaru HD（男性） | ★高品質 |

### 英語

| ボイス ID | 説明 | 品質 |
|-----------|------|------|
| `en-US-JennyNeural` | Jenny（女性） | 標準 |
| `en-US-GuyNeural` | Guy（男性） | 標準 |
| `en-US-AriaNeural` | Aria（女性） | 標準 |
| `en-US-DavisNeural` | Davis（男性） | 標準 |
| `en-US-EmmaNeural` | Emma（女性） | 標準 |
| `en-US-AndrewNeural` | Andrew（男性） | 標準 |
| `en-US-Ava:DragonHDLatestNeural` | Ava HD（女性） | ★高品質 |
| `en-US-Andrew:DragonHDLatestNeural` | Andrew HD（男性） | ★高品質 |

> ★ DragonHD ボイスは `eastus` / `eastus2` / `westeurope` リージョンのみ対応

## ユースケース別コマンド早見表

| 用途 | コマンド |
|------|---------|
| 1文をすぐ確認したい | `...tts.exe --language ja "テキスト"` |
| 高品質で保存したい | `...tts.exe --language ja --voice "ja-JP-Nanami:DragonHDLatestNeural" --output out.wav "テキスト"` |
| スクリプト全行を一括生成 | `...tts.exe --language ja --input-file script.txt --output output/` |
| 使えるボイスを確認したい | `...tts.exe --language ja --list-voices` |

※ `...tts.exe` は `$HOME/projects/dev/tts_app/.venv/Scripts/tts.exe` の略

## エラー対処

| エラー | 原因 | 対処 |
|--------|------|------|
| `AZURE_SPEECH_KEY not found` | `.env` 未設定 | `$HOME/projects/dev/tts_app/.env` を確認 |
| `Voice not available` | リージョン非対応 | DragonHD は `AZURE_SPEECH_REGION=eastus` が必要 |
| `.venv が存在しない` | 環境未構築 | `cd $HOME/projects/dev/tts_app` で `uv pip install --only-binary :all: -e .` を実行 |

## 他プロジェクトから参照する場合

このスキルを使いたいプロジェクトの `CLAUDE.md` に1行追記するだけ：

```markdown
## Tools
音声合成が必要な場合は `$HOME/.claude/skills/tts/SKILL.md` を読むこと。
```
