Add-Type -AssemblyName System.Windows.Forms
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.Visible = $true
$notify.ShowBalloonTip(5000, "ADA", "Task complete. Waiting for input.", [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Milliseconds 1500
$notify.Dispose()
