# ADA handover 共通ロジック。フックとテストから dot-source して使う。

function Get-LatestHandover {
    # handovers ディレクトリ内で最新の handover ファイル(YYYY-MM-DD_HHmm.md)のフルパスを返す。
    # 無ければ $null。README 等の非handover .md は無視する。
    param([string]$Dir)
    if (-not (Test-Path $Dir)) { return $null }
    $f = Get-ChildItem -Path $Dir -Filter '*.md' -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}_\d{4}' } |
        Sort-Object Name -Descending | Select-Object -First 1
    if ($f) { return $f.FullName } else { return $null }
}

function Get-AdaContextReloadText {
    # Builds the post-compaction context reload text.
    # - index.md: full content (pointer-only by design, safe)
    # - pending.md: NOT injected (deprecated; ada-board is the source of truth)
    # - latest handover: pointer line only, never the body (stale handover
    #   content after compaction has caused context pollution before)
    param([string]$AdaDir)

    $indexPath = Join-Path $AdaDir "index.md"
    $handoverDir = Join-Path $AdaDir "handovers"

    $output = @()

    if (Test-Path $indexPath) {
        $output += "=== ADA context reloaded after compaction ==="
        $output += "--- ~/.claude/ada/index.md ---"
        $output += Get-Content $indexPath -Raw -Encoding UTF8
    }

    $latestHandover = Get-LatestHandover $handoverDir
    if ($latestHandover) {
        $name = Split-Path $latestHandover -Leaf
        $output += "最新handover: $name — 今の作業に関連する場合のみ Read すること（パス: $latestHandover）"
    }

    if ($output.Count -gt 0) {
        return ($output -join "`n")
    }
    return ""
}
