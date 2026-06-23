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
