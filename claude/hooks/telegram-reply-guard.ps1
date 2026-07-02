# telegram-reply-guard.ps1
# Purpose: Stop hook that prevents stopping when a Telegram-originated turn
#          has not been answered via the reply tool.
# Author: ADA (Claude Code)
# Approved: 2026-06-17 (perf/detection rework: 2026-07-02)
#
# Logic: delegated to Get-ReplyGuardDecision in telegram-reply-guard-lib.ps1
# (dot-sourced below). See that file for the comparison logic:
#   - last incoming Telegram message marker (role-agnostic; a known bug
#     can record incoming messages as type="assistant")
#   - last reply tool call (assistant, tool_use name=mcp__plugin_telegram_telegram__reply)
# If the incoming message is newer (i.e. not yet replied), block the stop.
# MUST run under pwsh (PowerShell 7): Windows PowerShell 5.1's ConvertFrom-Json
# silently fails on many transcript lines (large/Unicode content), which made the
# guard miss recent replies and block falsely. If launched under 5.x this script
# re-executes itself under pwsh. ASCII-only on purpose.

param([string]$StdinFile)

$ErrorActionPreference = 'Stop'

$logFile = 'C:\Users\nov26\.claude\hooks\telegram-reply-guard.log'
function Write-GuardLog([string]$msg) {
    try { Add-Content -LiteralPath $logFile -Value ("{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg) } catch {}
}
# Rotate: when the log exceeds maxBytes, keep only the last keepLines (cheap size check first).
function Rotate-Log([string]$path, [long]$maxBytes, [int]$keepLines) {
    try {
        if (-not (Test-Path -LiteralPath $path)) { return }
        if ((Get-Item -LiteralPath $path).Length -le $maxBytes) { return }
        $tail = Get-Content -LiteralPath $path -Tail $keepLines
        Set-Content -LiteralPath $path -Value $tail -Encoding utf8
    } catch {}
}
Rotate-Log $logFile 262144 1000

try {
    Write-GuardLog 'HOOK INVOKED'
    if ($StdinFile) {
        $raw = [System.IO.File]::ReadAllText($StdinFile, [System.Text.Encoding]::UTF8)
    }
    else {
        $stdin = New-Object System.IO.StreamReader ([Console]::OpenStandardInput()), ([System.Text.Encoding]::UTF8)
        $raw = $stdin.ReadToEnd()
    }

    if ($PSVersionTable.PSVersion.Major -lt 7) {
        Write-GuardLog 'Under PS 5.x; re-executing under pwsh 7'
        $tmp = [System.IO.Path]::GetTempFileName()
        [System.IO.File]::WriteAllText($tmp, $raw, (New-Object System.Text.UTF8Encoding($false)))
        try { $out = & pwsh -NoProfile -File $PSCommandPath -StdinFile $tmp }
        catch { Write-GuardLog ("pwsh re-exec failed -> allow : {0}" -f $_.Exception.Message); Remove-Item -LiteralPath $tmp -ErrorAction SilentlyContinue; exit 0 }
        Remove-Item -LiteralPath $tmp -ErrorAction SilentlyContinue
        if ($out) { Write-Output $out }
        exit 0
    }
    Write-GuardLog ("stdin length = {0}" -f ($raw | Measure-Object -Character).Characters)
    if ([string]::IsNullOrWhiteSpace($raw)) { Write-GuardLog 'EXIT: empty stdin -> allow'; exit 0 }

    $data = $raw | ConvertFrom-Json

    # If we already blocked once this stop cycle, allow to avoid a hard lock.
    if ($data.stop_hook_active -eq $true) { Write-GuardLog 'EXIT: stop_hook_active -> allow'; exit 0 }

    $tp = $data.transcript_path
    Write-GuardLog ("transcript_path = {0}" -f $tp)
    if (-not $tp -or -not (Test-Path -LiteralPath $tp)) { Write-GuardLog 'EXIT: no transcript -> allow'; exit 0 }

    . (Join-Path $PSScriptRoot 'telegram-reply-guard-lib.ps1')

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $decision = Get-ReplyGuardDecision -TranscriptPath $tp
    $sw.Stop()

    Write-GuardLog ("DECISION: {0} ({1} ms)" -f $decision, $sw.ElapsedMilliseconds)

    if ($decision -eq 'block') {
        $reason = 'Unsent Telegram reply: you have NOT called the reply tool (mcp__plugin_telegram_telegram__reply) for the latest incoming Telegram message. Plain transcript text never reaches the user. Before stopping, you MUST send your answer to Telegram via the reply tool.'
        $out = @{ decision = 'block'; reason = $reason } | ConvertTo-Json -Compress
        Write-Output $out
        exit 0
    }

    exit 0
}
catch {
    # Never block the agent because the hook itself failed.
    Write-GuardLog ("EXIT: exception -> allow : {0}" -f $_.Exception.Message)
    exit 0
}
