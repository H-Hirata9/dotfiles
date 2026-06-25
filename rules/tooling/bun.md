## JavaScript/TypeScript Tooling: bun

- パッケージ追加: `bun add <package>`（`npm install` は使わない）
- パッケージ削除: `bun remove <package>`
- スクリプト実行: `bun run <script>` または `bun <file>`
- パッケージ実行: `bun x <package>`（`npx` は使わない）
- 新規プロジェクト: `bun init`
- テスト実行: `bun test`（組み込みテストランナーを使う）
- ロックファイル: `bun.lock`（テキスト形式・コミットする。旧 `bun.lockb` のリポもある）
- `npm`・`yarn`・`pnpm` は使わない
- ただし既存プロジェクトがコミット済みロックファイルで別マネージャを使っている場合はそれに従う（install 前に `git ls-files | grep -iE 'lock|bun'` で判定）
