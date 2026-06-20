#!/usr/bin/env bash
set -euo pipefail

DOTFILES="$(cd "$(dirname "$0")" && pwd)"
FORCE=false
DRY_RUN=false
SUBCOMMAND=""
INIT_TEMPLATE="base"
INIT_PATH="."

_pos=()
for arg in "$@"; do
  case $arg in
    --force)   FORCE=true ;;
    --dry-run) DRY_RUN=true ;;
    *)         _pos+=("$arg") ;;
  esac
done

[[ ${#_pos[@]} -gt 0 ]] && SUBCOMMAND="${_pos[0]}"
if [[ "$SUBCOMMAND" == "init-project" ]]; then
  [[ ${#_pos[@]} -gt 1 ]] && INIT_TEMPLATE="${_pos[1]}"
  [[ ${#_pos[@]} -gt 2 ]] && INIT_PATH="${_pos[2]}"
fi

status() { printf '[%s] %s\n' "$1" "$2"; }

smart_link() {
  local target="$1"
  local source="$2"

  if [[ ! -e "$source" ]]; then
    status ERROR "Source not found: $source"
    return
  fi

  local target_dir
  target_dir="$(dirname "$target")"
  if [[ ! -d "$target_dir" ]]; then
    if $DRY_RUN; then
      status DryRun "Would create directory: $target_dir"
    else
      mkdir -p "$target_dir"
    fi
  fi

  if [[ -e "$target" || -L "$target" ]]; then
    if ! $FORCE; then
      status Skip "Already exists: $target"
      return
    fi
    if ! $DRY_RUN; then
      local backup="${target}.bak.$(date +%Y%m%d%H%M%S)"
      mv "$target" "$backup"
      status Backup "$target -> $backup"
    fi
  fi

  if $DRY_RUN; then
    status DryRun "Would link: $target -> $source"
    return
  fi

  ln -sf "$source" "$target"
  status SymLink "$target -> $source"
}

build_agents_md() {
  local rules_dir="$DOTFILES/rules"
  local dest="$DOTFILES/codex/AGENTS.md"

  local sub_files=(
    "tone/tundere-jp.md"
    "coding.md"
    "git.md"
    "security.md"
    "workflow.md"
  )

  if $DRY_RUN; then
    status DryRun "Would regenerate: $dest"
    return
  fi

  mkdir -p "$DOTFILES/codex"

  {
    cat <<'HEADER'
# Agent Instructions

<!-- このファイルは setup.sh により自動生成されます。直接編集しないこと。
     編集は rules/ 以下の各ファイルへ。 -->

このファイルは Claude Code / OpenAI Codex / GitHub Copilot / Antigravity の
共通ルールを定義します。

HEADER

    local first=true
    for f in "${sub_files[@]}"; do
      local path="$rules_dir/$f"
      if [[ -f "$path" ]]; then
        if ! $first; then printf '\n\n---\n\n'; fi
        cat "$path"
        first=false
      else
        status WARN "Missing: $path" >&2
      fi
    done
    printf '\n'
  } > "$dest"

  status Generated "$dest"
}

build_gemini_md() {
  local rules_dir="$DOTFILES/rules"
  local dest="$DOTFILES/gemini/GEMINI.md"

  local sub_files=(
    "tone/tundere-jp.md"
    "coding.md"
    "git.md"
    "security.md"
    "workflow.md"
  )

  if $DRY_RUN; then
    status DryRun "Would regenerate: $dest"
    return
  fi

  mkdir -p "$DOTFILES/gemini"

  {
    cat <<'HEADER'
# Gemini / Antigravity Rules

<!-- このファイルは setup.sh により自動生成されます。直接編集しないこと。
     編集は rules/ 以下の各ファイルへ。 -->

HEADER

    local first=true
    for f in "${sub_files[@]}"; do
      local path="$rules_dir/$f"
      if [[ -f "$path" ]]; then
        if ! $first; then printf '\n\n---\n\n'; fi
        cat "$path"
        first=false
      else
        status WARN "Missing: $path" >&2
      fi
    done
    printf '\n'
  } > "$dest"

  status Generated "$dest"
}

init_project() {
  local tmpl="$1"
  local path="$2"
  local template_file="$DOTFILES/templates/project/${tmpl}.md"
  local dest_dir="${path}/.claude"
  local dest_md="${dest_dir}/CLAUDE.md"
  local dest_gi="${path}/.gitignore"
  local snippet="$DOTFILES/templates/project/gitignore-snippet.txt"

  if [[ ! -f "$template_file" ]]; then
    status ERROR "テンプレートが見つかりません: $tmpl ($template_file)"
    printf 'Available: base, python, typescript\n'
    exit 1
  fi

  if $DRY_RUN; then
    status DryRun "Would create: $dest_dir"
  else
    mkdir -p "$dest_dir"
  fi

  if [[ -e "$dest_md" ]]; then
    status Skip "Already exists: $dest_md"
  elif $DRY_RUN; then
    status DryRun "Would create: $dest_md"
  else
    cp "$template_file" "$dest_md"
    status Created "$dest_md"
  fi

  if [[ -f "$dest_gi" ]] && grep -qF 'settings.local.json' "$dest_gi"; then
    status Skip ".gitignore already has Claude entries"
  elif $DRY_RUN; then
    status DryRun "Would append Claude entries to: $dest_gi"
  else
    [[ -f "$dest_gi" ]] && printf '\n' >> "$dest_gi"
    cat "$snippet" >> "$dest_gi"
    status Updated "$dest_gi"
  fi

  # Antigravity .agents/rules/
  local agents_dir="${path}/.agents/rules"
  if $DRY_RUN; then
    status DryRun "Would create: $agents_dir"
  else
    mkdir -p "$agents_dir"
  fi

  local agents_project="${agents_dir}/project.md"
  if [[ -e "$agents_project" ]]; then
    status Skip "Already exists: $agents_project"
  elif $DRY_RUN; then
    status DryRun "Would create: $agents_project"
  else
    cp "$DOTFILES/templates/project/base.md" "$agents_project"
    status Created "$agents_project"
  fi

  local tooling_src=""
  case "$tmpl" in
    python)     tooling_src="$DOTFILES/rules/tooling/uv.md" ;;
    typescript) tooling_src="$DOTFILES/rules/tooling/bun.md" ;;
  esac

  if [[ -n "$tooling_src" ]]; then
    local agents_tooling="${agents_dir}/tooling.md"
    if [[ -e "$agents_tooling" ]]; then
      status Skip "Already exists: $agents_tooling"
    elif $DRY_RUN; then
      status DryRun "Would create: $agents_tooling"
    else
      cp "$tooling_src" "$agents_tooling"
      status Created "$agents_tooling"
    fi
  fi

  printf '\nプロジェクト設定を作成しました: %s\n' "$dest_md"
  printf '[PROJECT_NAME] などのプレースホルダーを書き換えてください。\n\n'
}

setup_secret_scan_hook() {
  # global core.hooksPath を dotfiles/git-hooks に向け、全リポの commit 時に
  # gitleaks で staged の秘密混入をブロックする。gitleaks 本体の導入は OS 依存のため別途。
  local hooks_dir="$DOTFILES/git-hooks"
  if $DRY_RUN; then
    status DryRun "Would set: git config --global core.hooksPath $hooks_dir"
    return
  fi
  git config --global core.hooksPath "$hooks_dir"
  status GitHook "core.hooksPath -> $hooks_dir"
  if ! command -v gitleaks >/dev/null 2>&1; then
    status WARN "gitleaks 未インストール。導入してください (brew install gitleaks など)"
  fi
}

if [[ "$SUBCOMMAND" == "init-project" ]]; then
  echo ''
  echo "init-project: template=$INIT_TEMPLATE path=$INIT_PATH"
  if $DRY_RUN; then echo '[DryRun モード]'; fi
  echo ''
  init_project "$INIT_TEMPLATE" "$INIT_PATH"
else
  echo ''
  echo 'dotfiles セットアップ開始'
  echo "DotfilesRoot: $DOTFILES"
  if $DRY_RUN; then echo '[DryRun モード - 変更は行いません]'; fi
  echo ''

  echo '  AGENTS.md 生成中...'
  build_agents_md

  echo '  GEMINI.md 生成中...'
  build_gemini_md

  links=(
    "$HOME/.claude/CLAUDE.md|$DOTFILES/claude/CLAUDE.md"
    "$HOME/.claude/settings.json|$DOTFILES/claude/settings.json"
    "$HOME/.codex/AGENTS.md|$DOTFILES/codex/AGENTS.md"
    "$HOME/.gemini/GEMINI.md|$DOTFILES/gemini/GEMINI.md"
    "$HOME/.claude/rules|$DOTFILES/rules"
  )

  for entry in "${links[@]}"; do
    target="${entry%%|*}"
    source="${entry##*|}"
    smart_link "$target" "$source"
  done

  echo '  gitleaks pre-commit hook (秘密スキャン)'
  setup_secret_scan_hook

  echo ''
  echo 'セットアップ完了！'
  echo 'Claude Code を再起動して変更を反映してください。'
  echo ''
fi
