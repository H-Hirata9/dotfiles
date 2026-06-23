# ada-precompact.ps1
# Purpose: PreCompact hook. On AUTO compaction only, notify the owner on Telegram
#          in ADA's voice that context is about to be compacted.
# Author: ADA (Claude Code)
# Approved: 2026-06-19
#
# Notes:
# - Manual /compact is owner-initiated, so no notification is sent for it.
# - The message text lives in ada-precompact-msg.txt (UTF-8) to keep this script ASCII.
# - Token/chat come from env (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID).
# - This hook NEVER fails the compaction: any error -> exit 0 silently.
# - Run under pwsh 7 (registered with `pwsh` in settings.json).

param([string]$StdinFile)

$ErrorActionPreference = 'SilentlyContinue'

try {
    if ($StdinFile) {
        $raw = [System.IO.File]::ReadAllText($StdinFile, [System.Text.Encoding]::UTF8)
    }
    else {
        $sr = New-Object System.IO.StreamReader ([Console]::OpenStandardInput()), ([System.Text.Encoding]::UTF8)
        $raw = $sr.ReadToEnd()
    }

    if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }
    $data = $raw | ConvertFrom-Json

    # Only notify on automatic compaction; skip owner-initiated /compact.
    if ($data.trigger -ne 'auto') { exit 0 }

    $token = $env:TELEGRAM_BOT_TOKEN
    $chat = $env:TELEGRAM_CHAT_ID
    if (-not $token -or -not $chat) { exit 0 }

    $msgPath = Join-Path $PSScriptRoot 'ada-precompact-msg.txt'
    if (-not (Test-Path -LiteralPath $msgPath)) { exit 0 }
    $text = [System.IO.File]::ReadAllText($msgPath, [System.Text.Encoding]::UTF8)

    $body = @{ chat_id = $chat; text = $text } | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
    $uri = "https://api.telegram.org/bot$token/sendMessage"
    Invoke-RestMethod -Uri $uri -Method Post -Body $bytes -ContentType 'application/json; charset=utf-8' | Out-Null
}
catch {}

exit 0
