## 口調の設定
@/rules/tone/ada-jp.md
## コーディングの設定
@/rules/coding.md
## Gitの設定
@/rules/git.md
## セキュリティに関する考慮事項
@./rules/security.md
## ワークフロー
@./rules/workflow.md
## ツール設定（JS/TS=bun, Python=uv）
@/rules/tooling/bun.md
@/rules/tooling/uv.md

---

## Claude Code Specific

- 複雑なタスクは plan mode で計画を立ててから実行する
- ファイルを変更する前に何をするか伝えてから実行する
- `~/.claude/plans/` に作業計画を保存する
- メモリシステム (`~/.claude/projects/*/memory/`) を活用してコンテキストを維持する
