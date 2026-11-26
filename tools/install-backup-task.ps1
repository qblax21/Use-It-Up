# Schedules the daily pantry backup (Windows Task Scheduler, current user, no admin needed).
#   powershell -ExecutionPolicy Bypass -File tools\install-backup-task.ps1 [-At 21:00] [-BackupDir D:\UseItUpBackups]
# If the PC is off or asleep at that time, the backup runs as soon as it's back on.
# Remove with: Unregister-ScheduledTask -TaskName 'UseItUp pantry backup' -Confirm:$false
param([string]$At = '21:00', [string]$BackupDir = 'D:\UseItUpBackups')
$ErrorActionPreference = 'Stop'
$dir = Join-Path $env:USERPROFILE 'UseItUp'
New-Item -ItemType Directory -Force $dir | Out-Null
$script = Join-Path $dir 'backup-pantry.ps1'
Copy-Item (Join-Path $PSScriptRoot 'backup-pantry.ps1') $script -Force
Copy-Item (Join-Path $PSScriptRoot 'restore-pantry.ps1') (Join-Path $dir 'restore-pantry.ps1') -Force

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`" -BackupDir `"$BackupDir`""
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName 'UseItUp pantry backup' -Action $action -Trigger $trigger -Settings $settings -Description 'Daily zip of the Use It Up shared pantry (keeps 14).' -Force | Out-Null
"Scheduled daily at $At -> $BackupDir. Running one backup now:"
Start-ScheduledTask -TaskName 'UseItUp pantry backup'
Start-Sleep 5
Get-ChildItem $BackupDir -Filter 'pantry-*.zip' -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 3 Name, Length, LastWriteTime | Format-Table -AutoSize
