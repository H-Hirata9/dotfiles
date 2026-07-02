# TDD: ada-guard.ps1 quote-bypass hardening tests
$ErrorActionPreference = 'Stop'

$script:fail = 0
function Assert-Eq($actual, $expected, $name) {
    if ($actual -ne $expected) { Write-Host "FAIL: $name (expected '$expected', got '$actual')"; $script:fail++ }
    else { Write-Host "PASS: $name" }
}

$guardScript = Join-Path $PSScriptRoot '..\ada-guard.ps1'
$testLog = Join-Path $env:TEMP ("ada_guard_test_" + [guid]::NewGuid().ToString('N') + '.log')
$env:ADA_GUARD_LOG = $testLog

function Invoke-Guard([string]$cmd) {
    $jsonFile = Join-Path $env:TEMP ("ada_guard_input_" + [guid]::NewGuid().ToString('N') + '.json')
    try {
        $payload = @{ tool_input = @{ command = $cmd } } | ConvertTo-Json -Compress
        Set-Content -LiteralPath $jsonFile -Value $payload -Encoding utf8 -NoNewline
        Get-Content -LiteralPath $jsonFile -Raw | pwsh -NoProfile -File $guardScript | Out-Null
        return $LASTEXITCODE
    } finally {
        Remove-Item -LiteralPath $jsonFile -Force -ErrorAction SilentlyContinue
    }
}

try {
    # ---- BLOCK cases (exit 2) ----
    Assert-Eq (Invoke-Guard 'rm -rf /') 2 'BLOCK: rm -rf / (regression)'
    Assert-Eq (Invoke-Guard 'git push --force origin main') 2 'BLOCK: git push --force (regression)'
    Assert-Eq (Invoke-Guard 'pwsh -Command "Remove-Item C:\Users\nov26 -Recurse -Force"') 2 'BLOCK: pwsh -Command quote bypass'
    Assert-Eq (Invoke-Guard 'bash -c "rm -rf ~"') 2 'BLOCK: bash -c double-quote bypass'
    Assert-Eq (Invoke-Guard "bash -c 'rm -rf /'") 2 'BLOCK: bash -c single-quote bypass'
    Assert-Eq (Invoke-Guard 'powershell -EncodedCommand SQBFAFgAIAB4AA==') 2 'BLOCK: powershell -EncodedCommand'
    Assert-Eq (Invoke-Guard 'pwsh -enc SQBFAFgA') 2 'BLOCK: pwsh -enc'

    # ---- ALLOW cases (exit 0) ----
    Assert-Eq (Invoke-Guard 'python worklog.py --did "today we blocked git push --force"') 0 'ALLOW: worklog prose arg no false-positive'
    Assert-Eq (Invoke-Guard 'git commit -m "docs: add notes about rm -rf protection"') 0 'ALLOW: git commit prose message no false-positive'
    Assert-Eq (Invoke-Guard 'Remove-Item C:\Users\nov26\projects\tmp\x.txt') 0 'ALLOW: plain Remove-Item (audit only)'
    Assert-Eq (Invoke-Guard 'pwsh -Command "Get-ChildItem C:\Users\nov26"') 0 'ALLOW: pwsh -Command benign payload'
    Assert-Eq (Invoke-Guard 'powershell -ExecutionPolicy Bypass -File script.ps1') 0 'ALLOW: -ExecutionPolicy not mistaken for -EncodedCommand'
    Assert-Eq (Invoke-Guard '') 0 'ALLOW: empty command'
}
finally {
    Remove-Item -LiteralPath $testLog -Force -ErrorAction SilentlyContinue
    Remove-Item Env:\ADA_GUARD_LOG -ErrorAction SilentlyContinue
}

if ($script:fail -gt 0) { Write-Host "`n$($script:fail) test(s) failed"; exit 1 } else { Write-Host "`nAll tests passed"; exit 0 }
