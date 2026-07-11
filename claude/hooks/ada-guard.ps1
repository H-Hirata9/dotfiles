# ada-guard.ps1 - PreToolUse safety hook (Case A)
# Hard-blocks ONLY catastrophic commands; audit-logs other destructive ops; allows everything else.
# Contract: exit 2 = block (reason on stderr); exit 0 = allow. Fails open on errors.
# stdin: JSON with .tool_input.command  (matcher: Bash|PowerShell)
# Scan strategy: quoted string literals are stripped first (so prose args like
# worklog --did "..." don't false-positive), then quoted payloads that follow an
# exec flag (pwsh -Command "...", bash -c "...") are re-added, since those are
# actually executed and must not escape detection via quoting alone.
# Set $env:ADA_GUARD_LOG to override the audit log path (used by tests).

$ErrorActionPreference = 'Stop'
$logFile = Join-Path $PSScriptRoot 'ada-guard.log'
if ($env:ADA_GUARD_LOG) { $logFile = $env:ADA_GUARD_LOG }

function Write-Audit([string]$decision, [string]$pattern, [string]$cmd) {
    try {
        # rotate: keep last 1000 lines when over 256KB (cheap size check first)
        if ((Test-Path -LiteralPath $logFile) -and ((Get-Item -LiteralPath $logFile).Length -gt 262144)) {
            $tail = Get-Content -LiteralPath $logFile -Tail 1000
            Set-Content -LiteralPath $logFile -Value $tail -Encoding utf8
        }
        $line = '{0}  {1,-6}  {2}  ::  {3}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $decision, $pattern, $cmd
        Add-Content -LiteralPath $logFile -Value $line -Encoding utf8
    } catch { }
}

try {
    # stdin を UTF-8 明示で読む（コンソール既定だと CP932 で日本語が壊れる）
    $reader = New-Object System.IO.StreamReader([Console]::OpenStandardInput(), [System.Text.Encoding]::UTF8)
    $raw = $reader.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }
    $j = $raw | ConvertFrom-Json
    $cmd = [string]$j.tool_input.command
    if ([string]::IsNullOrWhiteSpace($cmd)) { exit 0 }
} catch {
    # parse failure -> fail open
    exit 0
}

# Scan with quoted string literals removed, so dangerous tokens that merely appear
# inside arguments (e.g. a worklog --did "...git push --force...") are not flagged.
# Real catastrophic commands (rm -rf /) are not normally quoted, so they still match.
$scan = $cmd -replace '"[^"]*"', '' -replace "'[^']*'", ''

# Quote-stripping must not hide payloads that are EXECUTED (pwsh -Command "...",
# bash -c '...', node -e "..."). Extract quoted strings that directly follow an
# exec flag and scan them too. Prose arguments (worklog --did "...") are not
# preceded by an exec flag, so they stay excluded.
$payloadRe = '(?i)(?:^|[\s;|&(])(?:-{1,2}command|-c|/c|-e|--eval|iex|invoke-expression)\s+(?:"([^"]*)"|''([^'']*)'')'
$payloads = @()
foreach ($m in [regex]::Matches($cmd, $payloadRe)) {
    foreach ($g in 1, 2) {
        if ($m.Groups[$g].Success -and $m.Groups[$g].Value) { $payloads += $m.Groups[$g].Value }
    }
}
if ($payloads.Count -gt 0) { $scan = $scan + "`n" + ($payloads -join "`n") }

# ---- CATASTROPHIC: hard block (no legitimate use) ----
# home patterns are built from $HOME so the guard works for any user/OS (was hardcoded nov26)
$homeNativeRe = [regex]::Escape($HOME)
$homePosixRe = if ($HOME -match '^[A-Za-z]:') {
    [regex]::Escape('/' + $HOME.Substring(0, 1).ToLower() + ($HOME.Substring(2) -replace '\\', '/'))
} else { $homeNativeRe }
$catastrophic = @(
    @{ name = 'rm -rf root/home/drive';      re = '(?i)\brm\b[^;|&\n]*\s-[a-z]*r[a-z]*\s+(-[a-z]+\s+)*(/(\s|;|&|\||$)|~/?(\s|;|&|\||$)|\$\{?HOME\}?/?(\s|;|&|\||$)|' + $homePosixRe + '/?(\s|;|&|\||$)|[a-z]:[\\/]?(\s|;|&|\||$))' },
    @{ name = 'Remove-Item -Recurse -Force root/home'; re = '(?i)Remove-Item\b(?=[^;|\n]*-Recurse)(?=[^;|\n]*-Force)[^;|\n]*(\s|["''])([a-z]:\\?(\s|;|"|''|$)|~|\$HOME|\$env:USERPROFILE|' + $homeNativeRe + '(\\+)?(\s|;|"|''|$))' },
    @{ name = 'git push --force';            re = '(?i)git\s+push\b[^;|\n]*(--force(\s|$|[^-])|\s-f(\s|$))' },
    @{ name = 'fork bomb';                   re = ':\(\)\s*\{\s*:\s*\|\s*:?\s*&\s*\}' },
    @{ name = 'mkfs';                        re = '(?i)\bmkfs(\.\w+)?\b' },
    @{ name = 'dd to device';                re = '(?i)\bdd\b[^;|\n]*\bof=\s*/dev/' },
    @{ name = 'redirect to block device';    re = '(?i)>\s*/dev/(sd|nvme|disk|hd)' },
    @{ name = 'powershell -EncodedCommand'; re = '(?i)\b(?:powershell|pwsh)(?:\.exe)?\b[^;|&\n]*\s-e(?:c|nc(?:odedcommand)?)?(?=\s|$)' }
)
foreach ($p in $catastrophic) {
    if ($scan -match $p.re) {
        Write-Audit 'BLOCK' $p.name $cmd
        [Console]::Error.WriteLine("ada-guard: blocked catastrophic operation [$($p.name)]. This is never safe and cannot be auto-run. If you truly need it, ask the owner on Telegram and have THEM run it manually.")
        exit 2
    }
}

# ---- DESTRUCTIVE: audit-log only, allow (HITL prose still applies) ----
$destructive = @(
    @{ name = 'recursive rm';        re = '(?i)\brm\b[^;|&\n]*\s-[a-z]*r' },
    @{ name = 'Remove-Item -Recurse'; re = '(?i)Remove-Item\b[^;|\n]*-Recurse' },
    @{ name = 'shutil.rmtree';       re = 'shutil\.rmtree' },
    @{ name = 'os.remove/unlink';    re = '(?i)\bos\.(remove|unlink)\s*\(' },
    @{ name = 'git reset --hard';    re = '(?i)git\s+reset\b[^;|\n]*--hard' },
    @{ name = 'git clean -f';        re = '(?i)git\s+clean\b[^;|\n]*-[a-z]*f' },
    @{ name = 'git push --force-with-lease'; re = '(?i)git\s+push\b[^;|\n]*--force-with-lease' },
    @{ name = 'az delete';           re = '(?i)\baz\b[^;|\n]*\bdelete\b' },
    @{ name = 'rmdir /s';            re = '(?i)\brmdir\b[^;|\n]*/s' }
)
foreach ($p in $destructive) {
    if ($scan -match $p.re) {
        Write-Audit 'AUDIT' $p.name $cmd
        break
    }
}

exit 0
