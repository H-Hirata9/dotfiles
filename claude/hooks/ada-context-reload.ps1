$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

. "$PSScriptRoot\ada-handover-lib.ps1"

$text = Get-AdaContextReloadText "$env:USERPROFILE\.claude\ada"

if ($text) {
    Write-Output $text
}
