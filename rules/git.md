## Git Conventions

- コミットメッセージは Conventional Commits 形式
  - `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:` など
- `.env`、シークレット、ビルド成果物はコミットしない
- 明示的に指示されない限りコミットしない
- main/master に直接コミットしない。`<type>/<topic>`（`feature/`・`fix/`・`docs/`・`chore/` など）を切って PR にする
  - 理由: 差分をレビューでき、revert の単位が残る
  - PR本文は 背景 / 変更 / 検証 / 含めなかったもの の4節で書く
  - 直近のコミットが main 直だったことを根拠に直コミットを提案しない（先例ではなく規約に従う）
  - 例外は主人が直接コミットを明示指示したときのみ
