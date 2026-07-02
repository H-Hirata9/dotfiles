# TDD: Get-AdaContextReloadText の単体テスト
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\..\ada-handover-lib.ps1"

$script:fail = 0
function Assert-Contains($haystack, $needle, $name) {
    if ($haystack -like "*$needle*") { Write-Host "PASS: $name" }
    else { Write-Host "FAIL: $name (expected to contain '$needle')"; $script:fail++ }
}
function Assert-NotContains($haystack, $needle, $name) {
    if ($haystack -like "*$needle*") { Write-Host "FAIL: $name (expected NOT to contain '$needle')"; $script:fail++ }
    else { Write-Host "PASS: $name" }
}
function Assert-Eq($actual, $expected, $name) {
    if ($actual -ne $expected) { Write-Host "FAIL: $name (expected '$expected', got '$actual')"; $script:fail++ }
    else { Write-Host "PASS: $name" }
}

$tmp = Join-Path $env:TEMP ("ada_ctx_test_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
    # --- Fixture: index.md + pending.md + 2 handovers ---
    $tasksDir = Join-Path $tmp 'tasks'
    $handoverDir = Join-Path $tmp 'handovers'
    New-Item -ItemType Directory -Path $tasksDir | Out-Null
    New-Item -ItemType Directory -Path $handoverDir | Out-Null

    'INDEX_BODY_MARKER' | Set-Content (Join-Path $tmp 'index.md')
    'PENDING_BODY_MARKER' | Set-Content (Join-Path $tasksDir 'pending.md')
    'OLD_HANDOVER_BODY_MARKER' | Set-Content (Join-Path $handoverDir '2026-07-01_1200.md')
    'NEW_HANDOVER_BODY_MARKER' | Set-Content (Join-Path $handoverDir '2026-07-02_0900.md')

    $result = Get-AdaContextReloadText $tmp

    # 1. index.md body is included
    Assert-Contains $result 'INDEX_BODY_MARKER' "index.md body is included"

    # 2. pending.md body is NOT included
    Assert-NotContains $result 'PENDING_BODY_MARKER' "pending.md body is not included"

    # 3. handover body is NOT included (neither old nor new)
    Assert-NotContains $result 'OLD_HANDOVER_BODY_MARKER' "old handover body is not included"
    Assert-NotContains $result 'NEW_HANDOVER_BODY_MARKER' "new handover body is not included"

    # 4. pointer line references the latest handover filename; old filename absent
    Assert-Contains $result '2026-07-02_0900.md' "pointer line references latest handover filename"
    Assert-NotContains $result '2026-07-01_1200.md' "old handover filename is not referenced"

    # 5. index.md only (no handovers) -> pointer line absent, index body present
    $tmp2 = Join-Path $env:TEMP ("ada_ctx_test_" + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tmp2 | Out-Null
    try {
        'INDEX_ONLY_MARKER' | Set-Content (Join-Path $tmp2 'index.md')
        $result2 = Get-AdaContextReloadText $tmp2
        Assert-Contains $result2 'INDEX_ONLY_MARKER' "index-only: index body present"
        Assert-NotContains $result2 'handover' "index-only: no handover pointer line"
    }
    finally {
        Remove-Item $tmp2 -Recurse -Force
    }

    # 6. empty directory -> empty string, no error
    $tmp3 = Join-Path $env:TEMP ("ada_ctx_test_" + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tmp3 | Out-Null
    try {
        $result3 = Get-AdaContextReloadText $tmp3
        Assert-Eq $result3 '' "empty dir returns empty string"
    }
    finally {
        Remove-Item $tmp3 -Recurse -Force
    }
}
finally {
    Remove-Item $tmp -Recurse -Force
}

if ($script:fail -gt 0) { Write-Host "`n$($script:fail) test(s) failed"; exit 1 } else { Write-Host "`nAll tests passed"; exit 0 }
