# ADA Bootstrap — 新端末セットアップ手順

裸の端末から「動くADA」を再現するための手順書。
ライフサイクル別に2部構成:
- **第1部 層0 Bootstrap** = コード・設定（dotfilesでGit管理。`setup.ps1`で一括復元）
- **第2部 再認証 runbook** = 秘密・状態（版管理しない。端末ごとに入れ直す）

関連: ada-board #24（版管理・ポータビリティ）/ #25（フルバックアップ）

---

## 第1部: 層0 Bootstrap（コード・設定を動かすまで）

### 1. 前提ランタイム
| ツール | 用途 | 導入 |
|---|---|---|
| Git / gh | 版管理・GitHub | 公式インストーラ / `winget install GitHub.cli` |
| PowerShell 7 (pwsh) | フック・setup | `winget install Microsoft.PowerShell` |
| Claude Code | ADA本体 | 公式 |
| uv | Python ツール管理 | `winget install astral-sh.uv` |
| Bun | Node ツール | `irm bun.sh/install.ps1 \| iex` |
| gitleaks | 秘密スキャン | `setup.ps1` が winget で自動導入 |

### 2. 追加CLI（用途に応じて）
| CLI | 用途 |
|---|---|
| agy (Antigravity) | 設計相談・画像生成 |
| gws | Google Workspace（Gmail/Calendar/Drive/Tasks） |
| az (Azure CLI) | tts / Azure Functions |

### 3. dotfiles を展開
```powershell
git clone https://github.com/H-Hirata9/dotfiles.git $env:USERPROFILE\dotfiles
cd $env:USERPROFILE\dotfiles
.\setup.ps1 -DryRun    # 確認
.\setup.ps1 -Force     # 適用
```
`setup.ps1` がやること:
- `~/.claude/CLAUDE.md` `~/.claude/settings.json` をリンク
- `~/.claude/rules` `~/.claude/skills/<自作>` `~/.claude/hooks` を junction（vendor skillには触れない）
- `codex/AGENTS.md` `gemini/GEMINI.md` を ADA トーンで生成
- gitleaks を導入し global `core.hooksPath` を設定

### 4. データ/知識リポを clone（必要に応じて）
- `cch-bot-knowledge`（health / ai-news / eval のデータレイク）
- 各プロジェクト（telegram_cch_bot, nature_remo, health_sync, discord_mybot 等）

### 5. 検証
```powershell
uv run --project $env:USERPROFILE\.claude\skills\evaluator --dev pytest $env:USERPROFILE\.claude\skills\evaluator\tests\ -q
```
- Claude Code を再起動 → hooks 発火（無害コマンドで `~/.claude/hooks/ada-guard.log` に記録されるか）

---

## 第2部: 再認証 runbook（版管理しない秘密・状態）

コードと違い、秘密と状態は端末ごとに入れ直す。

### 認証（OAuth / ログイン）
| 対象 | 手順 |
|---|---|
| GitHub | `gh auth login` |
| Google (gws) | gws の初回認証（ブラウザ同意） |
| Google Health (health_sync) | `cd health_sync && uv run python auth.py`（ブラウザ同意。OAuth同意画面を Production 公開しておくと refresh token が失効しにくい） |
| Azure | `az login` |
| Antigravity (agy) | `agy` 初回ログイン |

### 秘密の復元（.env / トークン）
安全な保管先（パスワードマネージャ / 別バックアップ）から各プロジェクトの `.env` を復元:
- telegram_cch_bot / discord_mybot: Telegram / Discord bot token、各種 API キー
- nature_remo: Nature Remo トークン
- tts / Azure: Azure Speech キー 等

> 秘密は絶対に git に入れない（gitleaks pre-commit がブロックする）。

### 状態の復元（版管理外）
- **ADAの記憶** `~/.claude/ada/`（index / prefs / entities / knowledge / memory / handovers）
  → バックアップから復元（#25 フルバックアップ運用）。可変ステートなので Git ではなく同期/バックアップ対象
- **Task Scheduler 再登録**（Windows）:
  - `ADA-HealthFetch`（毎日 9:00, `health_sync/fetch_health.py`）
  - 診断士学習アラート（平日 21:00）
  - ※ Execute はコマンド名でなく**フルパス**で指定（タスク実行環境は PATH を継承しないことがある。`(Get-Command uv).Source` で確認）

### 検証チェックリスト
- [ ] `gh auth status` OK
- [ ] gws で予定取得できる
- [ ] evaluator pytest 緑
- [ ] hooks 発火（`ada-guard.log` に記録される）
- [ ] 主要スキル疎通（エアコン操作・session-search 等）

---

## 注意（ライフサイクル分離の原則）
- **層1 コード/設定** = Git（dotfiles）
- **層2 記憶/状態** = バックアップ/同期（Git にしない。競合と無意味なコミットで破綻する）
- **層3 秘密** = 版管理しない・端末ごと再認証
- 完全クロスプラットフォーム化は未対応（PowerShell フック・Task Scheduler は Windows 前提）
