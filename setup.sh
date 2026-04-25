#!/usr/bin/env bash
set -euo pipefail

DOTFILES="$(cd "$(dirname "$0")" && pwd)"
FORCE=false
DRY_RUN=false

for arg in "$@"; do
  case $arg in
    --force)   FORCE=true ;;
    --dry-run) DRY_RUN=true ;;
  esac
done

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

echo ''
echo 'dotfiles セットアップ開始'
echo "DotfilesRoot: $DOTFILES"
if $DRY_RUN; then echo '[DryRun モード - 変更は行いません]'; fi
echo ''

echo '  AGENTS.md 生成中...'
build_agents_md

links=(
  "$HOME/.claude/CLAUDE.md|$DOTFILES/claude/CLAUDE.md"
  "$HOME/.claude/settings.json|$DOTFILES/claude/settings.json"
  "$HOME/.codex/AGENTS.md|$DOTFILES/codex/AGENTS.md"
  "$HOME/.claude/rules|$DOTFILES/rules"
)

for entry in "${links[@]}"; do
  target="${entry%%|*}"
  source="${entry##*|}"
  smart_link "$target" "$source"
done

echo ''
echo 'セットアップ完了！'
echo 'Claude Code を再起動して変更を反映してください。'
echo ''
