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

.PARAMETER InitProject
    プロジェクト用 .claude/CLAUDE.md を生成する

.PARAMETER Template
    InitProject で使うテンプレート名 (base / python / typescript)

.PARAMETER ProjectPath
    InitProject の対象ディレクトリ（省略時はカレントディレクトリ）

.EXAMPLE
    .\setup.ps1 -DryRun
    .\setup.ps1 -Force
    .\setup.ps1 -InitProject -Template python -ProjectPath C:\work\myapp
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$Force,
    [switch]$DryRun,
    [switch]$InitProject,
    [string]$Template = 'base',
    [string]$ProjectPath = (Get-Location).Path
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
        'tone\ada-jp.md',
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

function Build-GeminiMd {
    param([string]$RulesDir, [string]$GeminiDir)

    $header = @"
# Gemini / Antigravity Rules

<!-- このファイルは setup.ps1 により自動生成されます。直接編集しないこと。
     編集は rules/ 以下の各ファイルへ。 -->

"@

    $subFiles = @(
        'tone\ada-jp.md',
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
    $dest = Join-Path $GeminiDir 'GEMINI.md'

    if ($DryRun) {
        Write-Status 'DryRun' "Would regenerate: $dest" 'Cyan'
        return
    }

    if (-not (Test-Path $GeminiDir)) {
        New-Item -ItemType Directory -Path $GeminiDir -Force | Out-Null
    }

    Set-Content -Path $dest -Value $content -Encoding UTF8
    Write-Status 'Generated' $dest 'Green'
}

function Start-ProjectInit {
    param([string]$TemplateType, [string]$Path)

    $TemplateFile = Join-Path $DotfilesRoot "templates\project\$TemplateType.md"
    $DestDir      = Join-Path $Path '.claude'
    $DestMd       = Join-Path $DestDir 'CLAUDE.md'
    $DestGi       = Join-Path $Path '.gitignore'
    $Snippet      = Join-Path $DotfilesRoot 'templates\project\gitignore-snippet.txt'

    if (-not (Test-Path $TemplateFile)) {
        Write-Status 'ERROR' "テンプレートが見つかりません: $TemplateType ($TemplateFile)" 'Red'
        Write-Host 'Available: base, python, typescript'
        exit 1
    }

    if ($DryRun) {
        Write-Status 'DryRun' "Would create: $DestDir" 'Cyan'
    } else {
        New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
    }

    if (Test-Path $DestMd) {
        Write-Status 'Skip' "Already exists: $DestMd" 'Gray'
    } elseif ($DryRun) {
        Write-Status 'DryRun' "Would create: $DestMd" 'Cyan'
    } else {
        Copy-Item $TemplateFile $DestMd
        Write-Status 'Created' $DestMd 'Green'
    }

    $hasEntry = (Test-Path $DestGi) -and (Select-String -Path $DestGi -Pattern 'settings\.local\.json' -Quiet)
    if ($hasEntry) {
        Write-Status 'Skip' '.gitignore already has Claude entries' 'Gray'
    } elseif ($DryRun) {
        Write-Status 'DryRun' "Would append Claude entries to: $DestGi" 'Cyan'
    } else {
        if (Test-Path $DestGi) { Add-Content -Path $DestGi -Value '' }
        Get-Content $Snippet | Add-Content -Path $DestGi
        Write-Status 'Updated' $DestGi 'Green'
    }

    # Antigravity .agents/rules/
    $AgentsDir = Join-Path $Path '.agents\rules'
    if ($DryRun) {
        Write-Status 'DryRun' "Would create: $AgentsDir" 'Cyan'
    } else {
        New-Item -ItemType Directory -Path $AgentsDir -Force | Out-Null
    }

    $AgentsProject = Join-Path $AgentsDir 'project.md'
    if (Test-Path $AgentsProject) {
        Write-Status 'Skip' "Already exists: $AgentsProject" 'Gray'
    } elseif ($DryRun) {
        Write-Status 'DryRun' "Would create: $AgentsProject" 'Cyan'
    } else {
        Copy-Item (Join-Path $DotfilesRoot 'templates\project\base.md') $AgentsProject
        Write-Status 'Created' $AgentsProject 'Green'
    }

    $ToolingSrc = switch ($TemplateType) {
        'python'     { Join-Path $DotfilesRoot 'rules\tooling\uv.md' }
        'typescript' { Join-Path $DotfilesRoot 'rules\tooling\bun.md' }
        default      { $null }
    }
    if ($ToolingSrc) {
        $AgentsTooling = Join-Path $AgentsDir 'tooling.md'
        if (Test-Path $AgentsTooling) {
            Write-Status 'Skip' "Already exists: $AgentsTooling" 'Gray'
        } elseif ($DryRun) {
            Write-Status 'DryRun' "Would create: $AgentsTooling" 'Cyan'
        } else {
            Copy-Item $ToolingSrc $AgentsTooling
            Write-Status 'Created' $AgentsTooling 'Green'
        }
    }

    Write-Host ''
    Write-Host "プロジェクト設定を作成しました: $DestMd" -ForegroundColor Green
    Write-Host '[PROJECT_NAME] などのプレースホルダーを書き換えてください。'
    Write-Host ''
}

function Set-SecretScanHook {
    # gitleaks を winget で導入し、global core.hooksPath を dotfiles/git-hooks に向ける。
    # これで全リポジトリの commit 時に staged の秘密混入をブロックする。
    $hooksDir = (Join-Path $DotfilesRoot 'git-hooks') -replace '\\', '/'

    $hasGitleaks = [bool](Get-Command gitleaks -ErrorAction SilentlyContinue)
    if (-not $hasGitleaks) {
        $wingetExe = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages\Gitleaks.Gitleaks_Microsoft.Winget.Source_8wekyb3d8bbwe\gitleaks.exe'
        $hasGitleaks = Test-Path $wingetExe
    }

    if (-not $hasGitleaks) {
        if ($DryRun) {
            Write-Status 'DryRun' 'Would: winget install Gitleaks.Gitleaks' 'Cyan'
        } else {
            Write-Status 'Install' 'gitleaks を winget で導入中...' 'DarkGray'
            winget install --id Gitleaks.Gitleaks --source winget --accept-package-agreements --accept-source-agreements --disable-interactivity | Out-Null
            Write-Status 'Install' 'gitleaks 導入完了' 'Green'
        }
    } else {
        Write-Status 'Skip' 'gitleaks はインストール済み' 'Gray'
    }

    if ($DryRun) {
        Write-Status 'DryRun' "Would set: git config --global core.hooksPath $hooksDir" 'Cyan'
    } else {
        git config --global core.hooksPath $hooksDir
        Write-Status 'GitHook' "core.hooksPath -> $hooksDir" 'Green'
    }
}

# --- メイン ---

if ($InitProject) {
    Write-Host ''
    Write-Host "init-project: template=$Template path=$ProjectPath"
    if ($DryRun) { Write-Host '[DryRun モード]' -ForegroundColor Yellow }
    Write-Host ''
    Start-ProjectInit -TemplateType $Template -Path $ProjectPath
} else {
    Write-Host ''
    Write-Host 'dotfiles セットアップ開始' -ForegroundColor White
    Write-Host "DotfilesRoot: $DotfilesRoot"
    if ($DryRun) { Write-Host '[DryRun モード - 変更は行いません]' -ForegroundColor Yellow }
    Write-Host ''

    Write-Host '  AGENTS.md 生成中...' -ForegroundColor DarkGray
    Build-AgentsMd -RulesDir (Join-Path $DotfilesRoot 'rules') -CodexDir (Join-Path $DotfilesRoot 'codex')

    Write-Host '  GEMINI.md 生成中...' -ForegroundColor DarkGray
    Build-GeminiMd -RulesDir (Join-Path $DotfilesRoot 'rules') -GeminiDir (Join-Path $DotfilesRoot 'gemini')

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
        },
        @{
            Target = Join-Path $UserProfile '.gemini\GEMINI.md'
            Source = Join-Path $DotfilesRoot 'gemini\GEMINI.md'
            Note   = 'Antigravity グローバルルール'
        }
    )

    foreach ($Link in $Links) {
        Write-Host "  $($Link.Note)" -ForegroundColor DarkGray
        New-SmartLink -Target $Link.Target -Source $Link.Source
    }

    Write-Host '  グローバル gitignore' -ForegroundColor DarkGray
    New-SmartLink `
        -Target (Join-Path $UserProfile '.config\git\ignore') `
        -Source (Join-Path $DotfilesRoot 'config\git\ignore')

    Write-Host '  ~/.claude/rules ジャンクション' -ForegroundColor DarkGray
    New-SmartJunction `
        -Target (Join-Path $UserProfile '.claude\rules') `
        -Source (Join-Path $DotfilesRoot 'rules')

    # 自作 Claude skills を per-skill junction（ada-skills サブモジュールから）
    # vendor skills（firecrawl-*, pptx, find-skills, skill-creator）は除外
    $VendorSkills = @(
        'firecrawl-build-interact', 'firecrawl-build-onboarding', 'firecrawl-build-scrape',
        'firecrawl-build-search', 'firecrawl-company-directories', 'firecrawl-competitive-intel',
        'firecrawl-dashboard-reporting', 'firecrawl-deep-research', 'firecrawl-demo-walkthrough',
        'firecrawl-knowledge-base', 'firecrawl-knowledge-ingest', 'firecrawl-lead-gen',
        'firecrawl-lead-research', 'firecrawl-market-research', 'firecrawl-qa',
        'firecrawl-research-papers', 'firecrawl-seo-audit', 'firecrawl-shop',
        'firecrawl-website-design-clone', 'firecrawl-workflows',
        'pptx', 'find-skills', 'skill-creator'
    )
    $SkillsSrcDir = Join-Path $DotfilesRoot 'claude\skills'
    $SkillsDstDir = Join-Path $UserProfile '.claude\skills'
    Write-Host '  自作 Claude skills ジャンクション (ada-skills サブモジュール)' -ForegroundColor DarkGray
    if (Test-Path $SkillsSrcDir -PathType Container) {
        Get-ChildItem $SkillsSrcDir -Directory | Where-Object { $VendorSkills -notcontains $_.Name } | ForEach-Object {
            New-SmartJunction -Target (Join-Path $SkillsDstDir $_.Name) -Source $_.FullName
        }
    } else {
        Write-Status 'WARN' "ada-skills submodule not initialized. Run: git submodule update --init" 'Yellow'
    }

    # 自作 Codex skills を per-skill junction（同じ ada-skills サブモジュールから）
    $CodexSkillsDstDir = Join-Path $UserProfile '.codex\skills'
    Write-Host '  自作 Codex skills ジャンクション (ada-skills サブモジュール)' -ForegroundColor DarkGray
    if (Test-Path $SkillsSrcDir -PathType Container) {
        if (-not (Test-Path $CodexSkillsDstDir)) {
            New-Item -ItemType Directory -Path $CodexSkillsDstDir -Force | Out-Null
        }
        Get-ChildItem $SkillsSrcDir -Directory | Where-Object { $VendorSkills -notcontains $_.Name } | ForEach-Object {
            New-SmartJunction -Target (Join-Path $CodexSkillsDstDir $_.Name) -Source $_.FullName
        }
    } else {
        Write-Status 'WARN' "ada-skills submodule not initialized. Run: git submodule update --init" 'Yellow'
    }

    Write-Host '  ~/.claude/hooks ジャンクション' -ForegroundColor DarkGray
    New-SmartJunction `
        -Target (Join-Path $UserProfile '.claude\hooks') `
        -Source (Join-Path $DotfilesRoot 'claude\hooks')

    Write-Host '  gitleaks pre-commit hook (秘密スキャン)' -ForegroundColor DarkGray
    Set-SecretScanHook

    # ADA 外部記憶リポジトリ（ada-memory）
    Write-Host '  ADA 外部記憶リポジトリ (ada-memory)' -ForegroundColor DarkGray
    $AdaMemoryDir = Join-Path $UserProfile '.claude\ada'
    $AdaMemoryRepo = 'https://github.com/H-Hirata9/ada-memory.git'
    if (Test-Path (Join-Path $AdaMemoryDir '.git')) {
        Write-Status 'Skip' "ada-memory は既にクローン済み: $AdaMemoryDir" 'Gray'
    } elseif ($DryRun) {
        Write-Status 'DryRun' "Would clone: $AdaMemoryRepo -> $AdaMemoryDir" 'Cyan'
    } else {
        git clone $AdaMemoryRepo $AdaMemoryDir
        Write-Status 'Cloned' "$AdaMemoryRepo -> $AdaMemoryDir" 'Green'
    }

    # retire_scan.py の依存関係インストール（uv sync）
    $UvExe = (Get-Command uv -ErrorAction SilentlyContinue)?.Source
    if ($UvExe -and (Test-Path (Join-Path $AdaMemoryDir 'pyproject.toml'))) {
        if ($DryRun) {
            Write-Status 'DryRun' "Would run: uv sync in $AdaMemoryDir" 'Cyan'
        } else {
            Push-Location $AdaMemoryDir
            uv sync
            Pop-Location
            Write-Status 'UvSync' "retire_scan.py 依存関係インストール完了" 'Green'
        }
    } elseif (-not $UvExe) {
        Write-Status 'WARN' "uv が見つかりません。手動で uv sync を実行してください: cd $AdaMemoryDir && uv sync" 'Yellow'
    }

    Write-Host ''
    Write-Host 'セットアップ完了！' -ForegroundColor Green
    Write-Host 'Claude Code を再起動して変更を反映してください。'
    Write-Host ''
}
