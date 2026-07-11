# TDD: Get-ReplyGuardDecision の単体テスト
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\..\telegram-reply-guard-lib.ps1"

$script:fail = 0
function Assert-Eq($actual, $expected, $name) {
    if ($actual -ne $expected) { Write-Host "FAIL: $name (expected '$expected', got '$actual')"; $script:fail++ }
    else { Write-Host "PASS: $name" }
}

function New-IncomingLine([string]$type, [string]$ts, [string]$text) {
    $obj = [ordered]@{
        type      = $type
        timestamp = $ts
        message   = @{
            content = @(
                @{ type = 'text'; text = $text }
            )
        }
    }
    return ($obj | ConvertTo-Json -Compress -Depth 10)
}

function New-ReplyLine([string]$ts) {
    $obj = [ordered]@{
        type      = 'assistant'
        timestamp = $ts
        message   = @{
            content = @(
                @{ type = 'tool_use'; name = 'mcp__plugin_telegram_telegram__reply'; input = @{} }
            )
        }
    }
    return ($obj | ConvertTo-Json -Compress -Depth 10)
}

$incomingText = '<channel source="plugin:telegram:telegram" chat_id="1">hello</channel>'

$tmp = Join-Path ([IO.Path]::GetTempPath())("trg_test_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null

function Write-Fixture([string]$name, [string[]]$lines) {
    $path = Join-Path $tmp $name
    Set-Content -LiteralPath $path -Value $lines -Encoding ascii
    return $path
}

try {
    # 1. incoming -> reply (reply newer) -> allow
    $f1 = Write-Fixture 'case1.jsonl' @(
        (New-IncomingLine 'user' '2026-07-02T10:00:00.000Z' $incomingText),
        (New-ReplyLine '2026-07-02T10:01:00.000Z')
    )
    Assert-Eq (Get-ReplyGuardDecision $f1) 'allow' 'case1: incoming then reply (reply newer) -> allow'

    # 2. incoming only (no reply) -> block
    $f2 = Write-Fixture 'case2.jsonl' @(
        (New-IncomingLine 'user' '2026-07-02T10:00:00.000Z' $incomingText)
    )
    Assert-Eq (Get-ReplyGuardDecision $f2) 'block' 'case2: incoming only, no reply -> block'

    # 3. reply then new incoming -> block
    $f3 = Write-Fixture 'case3.jsonl' @(
        (New-ReplyLine '2026-07-02T10:00:00.000Z'),
        (New-IncomingLine 'user' '2026-07-02T10:05:00.000Z' $incomingText)
    )
    Assert-Eq (Get-ReplyGuardDecision $f3) 'block' 'case3: reply then new incoming -> block'

    # 4. role bug: incoming recorded as type=assistant -> still detected -> block
    $f4 = Write-Fixture 'case4.jsonl' @(
        (New-IncomingLine 'assistant' '2026-07-02T10:00:00.000Z' $incomingText)
    )
    Assert-Eq (Get-ReplyGuardDecision $f4) 'block' 'case4: role-bug incoming (type=assistant) still detected -> block'

    # 5. line order reversed but reply timestamp is newer -> allow (timestamp, not order, decides)
    $f5 = Write-Fixture 'case5.jsonl' @(
        (New-ReplyLine '2026-07-02T10:05:00.000Z'),
        (New-IncomingLine 'user' '2026-07-02T10:00:00.000Z' $incomingText)
    )
    Assert-Eq (Get-ReplyGuardDecision $f5) 'allow' 'case5: reply line first in file but timestamp newer -> allow'

    # 6. no incoming telegram message at all -> allow
    $f6 = Write-Fixture 'case6.jsonl' @(
        (New-IncomingLine 'user' '2026-07-02T10:00:00.000Z' 'just a normal chat message, no telegram marker'),
        (New-ReplyLine '2026-07-02T10:01:00.000Z')
    )
    Assert-Eq (Get-ReplyGuardDecision $f6) 'allow' 'case6: no incoming telegram marker -> allow'

    # 7. corrupted line mixed in -> no exception, correct decision
    $f7 = Write-Fixture 'case7.jsonl' @(
        (New-IncomingLine 'user' '2026-07-02T10:00:00.000Z' $incomingText),
        '{this is not valid json, telegram plugin:telegram:telegram broken',
        (New-ReplyLine '2026-07-02T10:01:00.000Z')
    )
    $r7 = $null
    $threw = $false
    try { $r7 = Get-ReplyGuardDecision $f7 } catch { $threw = $true }
    Assert-Eq $threw $false 'case7: corrupted line does not throw'
    Assert-Eq $r7 'allow' 'case7: corrupted line skipped, correct decision (allow)'

    # 9. tag quoted inside a tool_use (Write input with fixture text) only -> allow
    $obj9 = [ordered]@{
        type      = 'assistant'
        timestamp = '2026-07-02T10:00:00.000Z'
        message   = @{
            content = @(
                @{ type = 'tool_use'; name = 'Write'; input = @{ file_path = 'C:/tmp/spec.md'; content = ('fixture doc quoting the tag: ' + $incomingText) } }
            )
        }
    }
    $f9 = Write-Fixture 'case9.jsonl' @(($obj9 | ConvertTo-Json -Compress -Depth 10))
    Assert-Eq (Get-ReplyGuardDecision $f9) 'allow' 'case9: tag quoted in tool_use input only, no real incoming -> allow'

    # 10. tag quoted inside a tool_result (Read output) only -> allow
    $obj10 = [ordered]@{
        type      = 'user'
        timestamp = '2026-07-02T10:00:00.000Z'
        message   = @{
            content = @(
                @{ type = 'tool_result'; tool_use_id = 'toolu_x'; content = ('file body quoting the tag: ' + $incomingText) }
            )
        }
    }
    $f10 = Write-Fixture 'case10.jsonl' @(($obj10 | ConvertTo-Json -Compress -Depth 10))
    Assert-Eq (Get-ReplyGuardDecision $f10) 'allow' 'case10: tag quoted in tool_result only, no real incoming -> allow'

    # 11. bare server id in metadata (attributionMcpServer) only, no channel tag -> allow
    #     Real-world case: the assistant text entry recorded around a reply call
    #     carries "attributionMcpServer":"plugin:telegram:telegram" as metadata.
    $obj11 = [ordered]@{
        type                 = 'assistant'
        timestamp            = '2026-07-02T10:00:00.000Z'
        attributionMcpServer = 'plugin:telegram:telegram'
        attributionMcpTool   = 'reply'
        message              = @{
            content = @(
                @{ type = 'text'; text = 'plain assistant text, no channel tag here' }
            )
        }
    }
    $f11 = Write-Fixture 'case11.jsonl' @(($obj11 | ConvertTo-Json -Compress -Depth 10))
    Assert-Eq (Get-ReplyGuardDecision $f11) 'allow' 'case11: bare server id in metadata only, no channel tag -> allow'

    # 8. performance smoke: 20k noise lines + a real incoming (no reply) -> block, and fast
    $noise = New-Object System.Collections.Generic.List[string]
    for ($i = 0; $i -lt 20000; $i++) {
        $obj = [ordered]@{ type = 'assistant'; timestamp = '2026-07-02T09:00:00.000Z'; message = @{ content = @(@{ type = 'text'; text = ("noise line number {0} with nothing interesting in it" -f $i) }) } }
        $noise.Add(($obj | ConvertTo-Json -Compress -Depth 10))
    }
    $noise.Add((New-IncomingLine 'user' '2026-07-02T10:00:00.000Z' $incomingText))
    $f8 = Join-Path $tmp 'case8.jsonl'
    Set-Content -LiteralPath $f8 -Value $noise -Encoding ascii

    $elapsed = Measure-Command { $script:r8 = Get-ReplyGuardDecision $f8 }
    Assert-Eq $script:r8 'block' 'case8: perf smoke, 20k noise lines + incoming, no reply -> block'
    Write-Host ("INFO: case8 perf smoke elapsed = {0} ms for 20001 lines" -f [math]::Round($elapsed.TotalMilliseconds, 1))
    if ($elapsed.TotalMilliseconds -gt 2000) {
        Write-Host "FAIL: case8 perf smoke too slow (>2000ms)"; $script:fail++
    }
    else {
        Write-Host "PASS: case8 perf smoke within budget"
    }
}
finally {
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

if ($script:fail -gt 0) { Write-Host "`n$($script:fail) test(s) failed"; exit 1 } else { Write-Host "`nAll tests passed"; exit 0 }
