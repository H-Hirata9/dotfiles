# TDD: Get-LatestHandover の単体テスト
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\..\ada-handover-lib.ps1"

$script:fail = 0
function Assert-Eq($actual, $expected, $name) {
    if ($actual -ne $expected) { Write-Host "FAIL: $name (expected '$expected', got '$actual')"; $script:fail++ }
    else { Write-Host "PASS: $name" }
}

$tmp = Join-Path $env:TEMP ("ada_ho_test_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
    Assert-Eq (Get-LatestHandover $tmp) $null "empty dir returns null"
    Assert-Eq (Get-LatestHandover (Join-Path $tmp 'nope')) $null "missing dir returns null"

    'a' | Set-Content (Join-Path $tmp '2026-06-19_0900.md')
    'b' | Set-Content (Join-Path $tmp '2026-06-20_1030.md')
    'c' | Set-Content (Join-Path $tmp '2026-06-20_0915.md')
    Assert-Eq (Split-Path (Get-LatestHandover $tmp) -Leaf) '2026-06-20_1030.md' "picks lexically-latest handover"

    'x' | Set-Content (Join-Path $tmp '2026-06-21_0000.txt')
    Assert-Eq (Split-Path (Get-LatestHandover $tmp) -Leaf) '2026-06-20_1030.md' "ignores non-md files"

    'readme' | Set-Content (Join-Path $tmp 'README.md')
    Assert-Eq (Split-Path (Get-LatestHandover $tmp) -Leaf) '2026-06-20_1030.md' "ignores non-timestamp md (README)"
}
finally {
    Remove-Item $tmp -Recurse -Force
}

if ($script:fail -gt 0) { Write-Host "`n$($script:fail) test(s) failed"; exit 1 } else { Write-Host "`nAll tests passed"; exit 0 }
