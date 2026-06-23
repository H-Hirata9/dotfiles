$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

. "$PSScriptRoot\ada-handover-lib.ps1"

$indexPath = "$env:USERPROFILE\.claude\ada\index.md"
$pendingPath = "$env:USERPROFILE\.claude\ada\tasks\pending.md"
$handoverDir = "$env:USERPROFILE\.claude\ada\handovers"

$output = @()

if (Test-Path $indexPath) {
    $output += "=== ADA context reloaded after compaction ==="
    $output += "--- ~/.claude/ada/index.md ---"
    $output += Get-Content $indexPath -Raw -Encoding UTF8
}

if (Test-Path $pendingPath) {
    $output += "--- ~/.claude/ada/tasks/pending.md ---"
    $output += Get-Content $pendingPath -Raw -Encoding UTF8
}

$latestHandover = Get-LatestHandover $handoverDir
if ($latestHandover) {
    $output += "--- 最新 handover ($(Split-Path $latestHandover -Leaf)) ---"
    $output += Get-Content $latestHandover -Raw -Encoding UTF8
}

if ($output.Count -gt 0) {
    Write-Output ($output -join "`n")
}
