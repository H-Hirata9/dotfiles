#Requires -Version 5.1

<#
.SYNOPSIS
    AI エージェント共通設定 dotfiles セットアップスクリプト

.DESCRIPTION
    Claude Code / OpenAI Codex / GitHub Copilot / Antigravity の
    設定ファイルへのリンクを作成します。

    リンク作成の優先順位:
    1. SymbolicLink (管理者権限 or Developer Mode が必要)
    2. HardLink (同一ドライブのファイルのみ、権限不要)
    3. Copy (フォールバック、変更後は再実行が必要)

.PARAMETER Force
    既存ファイル・ジャンクションをバックアップして上書きする

.PARAMETER DryRun
    実際には変更せず、何が行われるかを表示する

.EXAMPLE
    .\setup.ps1 -DryRun
    .\setup.ps1 -Force
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$DotfilesRoot = $PSScriptRoot
$UserProfile = [Environment]::GetFolderPath('UserProfile')

function Write-Status {
    param([string]$Type, [string]$Message, [string]$Color = 'White')
    Write-Host "[$Type] $Message" -ForegroundColor $Color
}

function New-SmartLink {
    param(
        [string]$Target,
        [string]$Source
    )

    if (-not (Test-Path $Source)) {
        if ($DryRun) {
            Write-Status 'DryRun' "Would link (source not yet generated): $Target -> $Source" 'Cyan'
        } else {
            Write-Status 'ERROR' "Source not found: $Source" 'Red'
        }
        return
    }

    $TargetDir = Split-Path $Target -Parent
    if (-not (Test-Path $TargetDir)) {
        if ($DryRun) {
            Write-Status 'DryRun' "Would create directory: $TargetDir" 'Gray'
        } else {
            New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
        }
    }

    if (Test-Path $Target) {
        if (-not $Force) {
            Write-Status 'Skip' "Already exists: $Target" 'Gray'
            return
        }
        if (-not $DryRun) {
            $Backup = "$Target.bak.$(Get-Date -Format 'yyyyMMddHHmmss')"
            Move-Item $Target $Backup
            Write-Status 'Backup' "$Target -> $Backup" 'Yellow'
        }
    }

    if ($DryRun) {
        Write-Status 'DryRun' "Would link: $Target -> $Source" 'Cyan'
        return
    }

    # 1. SymbolicLink を試みる
    try {
        New-Item -ItemType SymbolicLink -Path $Target -Value $Source -ErrorAction Stop | Out-Null
        Write-Status 'SymLink' "$Target -> $Source" 'Green'
        return
    } catch {}

    # 2. HardLink を試みる (ファイルのみ、同一ドライブ)
    $TargetDrive = Split-Path $Target -Qualifier
    $SourceDrive = Split-Path $Source -Qualifier
    if ($TargetDrive -eq $SourceDrive) {
        try {
            $null = & cmd /c "mklink /H `"$Target`" `"$Source`"" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Status 'HardLink' "$Target <=> $Source" 'Cyan'
                return
            }
        } catch {}
    }

    # 3. Copy にフォールバック
    Copy-Item $Source $Target
    Write-Status 'Copied' "$Target <- $Source" 'Magenta'
    Write-Warning "Copy を使用しました。$Source を変更したら setup.ps1 を再実行してください。"
}

function New-SmartJunction {
    param(
        [string]$Target,
        [string]$Source
    )

    if (-not (Test-Path $Source -PathType Container)) {
        Write-Status 'ERROR' "Source directory not found: $Source" 'Red'
        return
    }

    if (Test-Path $Target) {
        if (-not $Force) {
            Write-Status 'Skip' "Already exists: $Target" 'Gray'
            return
        }
        if (-not $DryRun) {
            Remove-Item $Target -Force -Recurse
            Write-Status 'Removed' $Target 'Yellow'
        }
    }

    if ($DryRun) {
        Write-Status 'DryRun' "Would create junction: $Target -> $Source" 'Cyan'
        return
    }

    New-Item -ItemType Junction -Path $Target -Value $Source | Out-Null
    Write-Status 'Junction' "$Target -> $Source" 'Green'
}

function Build-AgentsMd {
    param([string]$RulesDir, [string]$CodexDir)

    $header = @"
# Agent Instructions

<!-- このファイルは setup.ps1 により自動生成されます。直接編集しないこと。
     編集は rules/ 以下の各ファイルへ。 -->

このファイルは Claude Code / OpenAI Codex / GitHub Copilot / Antigravity の
共通ルールを定義します。

"@

    $subFiles = @(
        'tone\tundere-jp.md',
        'coding.md',
        'git.md',
        'security.md',
        'workflow.md'
    )

    $body = $subFiles | ForEach-Object {
        $path = Join-Path $RulesDir $_
        if (Test-Path $path) {
            Get-Content $path -Raw
        } else {
            Write-Status 'WARN' "Missing: $path" 'Yellow'
        }
    }

    $trimmedBody = ($body | ForEach-Object { $_.Trim() }) -join "`n`n---`n`n"
    $content = $header.TrimEnd() + "`n`n" + $trimmedBody + "`n"
    $dest = Join-Path $CodexDir 'AGENTS.md'

    if ($DryRun) {
        Write-Status 'DryRun' "Would regenerate: $dest" 'Cyan'
        return
    }

    if (-not (Test-Path $CodexDir)) {
        New-Item -ItemType Directory -Path $CodexDir -Force | Out-Null
    }

    Set-Content -Path $dest -Value $content -Encoding UTF8
    Write-Status 'Generated' $dest 'Green'
}

# --- メイン ---

Write-Host ''
Write-Host 'dotfiles セットアップ開始' -ForegroundColor White
Write-Host "DotfilesRoot: $DotfilesRoot"
if ($DryRun) { Write-Host '[DryRun モード - 変更は行いません]' -ForegroundColor Yellow }
Write-Host ''

Write-Host '  AGENTS.md 生成中...' -ForegroundColor DarkGray
Build-AgentsMd -RulesDir (Join-Path $DotfilesRoot 'rules') -CodexDir (Join-Path $DotfilesRoot 'codex')

$Links = @(
    @{
        Target = Join-Path $UserProfile '.claude\CLAUDE.md'
        Source = Join-Path $DotfilesRoot 'claude\CLAUDE.md'
        Note   = 'Claude Code グローバル指示'
    },
    @{
        Target = Join-Path $UserProfile '.claude\settings.json'
        Source = Join-Path $DotfilesRoot 'claude\settings.json'
        Note   = 'Claude Code 設定'
    },
    @{
        Target = Join-Path $UserProfile '.codex\AGENTS.md'
        Source = Join-Path $DotfilesRoot 'codex\AGENTS.md'
        Note   = 'OpenAI Codex グローバル指示'
    }
)

foreach ($Link in $Links) {
    Write-Host "  $($Link.Note)" -ForegroundColor DarkGray
    New-SmartLink -Target $Link.Target -Source $Link.Source
}

Write-Host '  ~/.claude/rules ジャンクション' -ForegroundColor DarkGray
New-SmartJunction `
    -Target (Join-Path $UserProfile '.claude\rules') `
    -Source (Join-Path $DotfilesRoot 'rules')

Write-Host ''
Write-Host 'セットアップ完了！' -ForegroundColor Green
Write-Host 'Claude Code を再起動して変更を反映してください。'
Write-Host ''
