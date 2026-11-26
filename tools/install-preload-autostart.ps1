# Makes Windows load the recipe model into GPU memory at login (and before lunch/dinner), so the first
# request from a phone doesn't wait about 2 minutes for the model to come off the D: hard disk.
#   powershell -ExecutionPolicy Bypass -File tools\install-preload-autostart.ps1 [-Model qwen2.5:14b] [-KeepAlive 4h] [-WarmAt '11:30,16:30']
# Delete UseItUp-Preload.vbs from your Startup folder to turn it off. Log: %USERPROFILE%\UseItUp\preload.log
param([string]$Model = 'qwen2.5:14b', [string]$KeepAlive = '4h', [string]$WarmAt = '11:30,16:30')
$ErrorActionPreference = 'Stop'

$dir = Join-Path $env:USERPROFILE 'UseItUp'
New-Item -ItemType Directory -Force $dir | Out-Null
$script = Join-Path $dir 'ollama-preload.ps1'
Copy-Item (Join-Path $PSScriptRoot 'ollama-preload.ps1') $script -Force

$vbs = @"
' Use It Up: loads $Model into GPU memory at login and at $WarmAt. Delete this file to stop it.
CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""$script"" -Model $Model -KeepAlive $KeepAlive -WarmAt ""$WarmAt""", 0, False
"@
$startup = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$target = Join-Path $startup 'UseItUp-Preload.vbs'
Set-Content -Path $target -Value $vbs -Encoding ASCII

Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'ollama-preload\.ps1' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Process wscript.exe -ArgumentList "`"$target`""
"Installed. $Model will load now and at each login; watch $dir\preload.log"
