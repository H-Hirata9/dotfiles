<#
.SYNOPSIS
    Claude Code のバックエンドを DeepSeek に切り替える／元に戻す

.DESCRIPTION
    Set  : ~/.claude/deepseek.env から DEEPSEEK_API_KEY を読んで環境変数をセット
    Unset: 環境変数を削除して Anthropic モードに戻す

    deepseek.env の書き方:
        DEEPSEEK_API_KEY=sk-xxxxxxxxxxxx

.PARAMETER Mode
    Set または Unset（省略時は Set）

.PARAMETER EnvFile
    .env ファイルのパス（省略時は ~/.claude/deepseek.env）

.EXAMPLE
    . .\Use-DeepSeek.ps1                      # Set（ドットソース必須）
    . .\Use-DeepSeek.ps1 -Mode Unset
    . .\Use-DeepSeek.ps1 -EnvFile C:\path\.env
#>

param(
    [ValidateSet('Set', 'Unset')]
    [string]$Mode = 'Set',
    [string]$EnvFile = (Join-Path $env:USERPROFILE '.claude\deepseek.env')
)

$Vars = @(
    'ANTHROPIC_BASE_URL',
    'ANTHROPIC_AUTH_TOKEN',
    'ANTHROPIC_MODEL',
    'ANTHROPIC_DEFAULT_OPUS_MODEL',
    'ANTHROPIC_DEFAULT_SONNET_MODEL',
    'ANTHROPIC_DEFAULT_HAIKU_MODEL',
    'CLAUDE_CODE_SUBAGENT_MODEL',
    'CLAUDE_CODE_EFFORT_LEVEL'
)

if ($Mode -eq 'Unset') {
    foreach ($v in $Vars) {
        Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
    }
    Write-Host '[DeepSeek] 環境変数をクリアしました。Anthropic モードに戻りました。' -ForegroundColor Yellow
    return
}

# .env から DEEPSEEK_API_KEY を読む
if (-not (Test-Path $EnvFile)) {
    Write-Error ".env ファイルが見つかりません: $EnvFile`n作成例: echo 'DEEPSEEK_API_KEY=sk-...' > $EnvFile"
    return
}

$key = $null
foreach ($line in (Get-Content $EnvFile -Encoding UTF8)) {
    if ($line -match '^\s*DEEPSEEK_API_KEY\s*=\s*(.+)$') {
        $key = $Matches[1].Trim().Trim('"').Trim("'")
        break
    }
}

if (-not $key) {
    Write-Error "$EnvFile に DEEPSEEK_API_KEY が見つかりません。"
    return
}

$env:ANTHROPIC_BASE_URL                = 'https://api.deepseek.com/anthropic'
$env:ANTHROPIC_AUTH_TOKEN              = $key
$env:ANTHROPIC_MODEL                   = 'deepseek-v4-pro[1m]'
$env:ANTHROPIC_DEFAULT_OPUS_MODEL      = 'deepseek-v4-pro[1m]'
$env:ANTHROPIC_DEFAULT_SONNET_MODEL    = 'deepseek-v4-pro[1m]'
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL     = 'deepseek-v4-flash'
$env:CLAUDE_CODE_SUBAGENT_MODEL        = 'deepseek-v4-flash'
$env:CLAUDE_CODE_EFFORT_LEVEL          = 'max'

Write-Host '[DeepSeek] 環境変数をセットしました。このシェルで claude を起動すると DeepSeek バックエンドで動きます。' -ForegroundColor Cyan
Write-Host "  BASE_URL : $env:ANTHROPIC_BASE_URL"
Write-Host "  MODEL    : $env:ANTHROPIC_MODEL"
