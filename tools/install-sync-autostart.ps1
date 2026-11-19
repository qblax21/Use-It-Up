# Installs the Use It Up pantry sync server so it starts at login and restarts itself if it stops (Windows).
#   powershell -ExecutionPolicy Bypass -File tools\install-sync-autostart.ps1 [-Port 11437]
# - Copies sync-server.py to %LOCALAPPDATA%\UseItUp; pantry data lives in %USERPROFILE%\UseItUpData (a few KB)
# - Writes a supervisor .vbs into your Startup folder (delete UseItUp-Sync.vbs to remove autostart)
# - Then add the Tailscale path route once:  tailscale serve --bg --set-path /sync http://127.0.0.1:11437
param([int]$Port = 11437)
$ErrorActionPreference = 'Stop'

$dir = Join-Path $env:LOCALAPPDATA 'UseItUp'
New-Item -ItemType Directory -Force $dir | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'sync-server.py') (Join-Path $dir 'sync-server.py') -Force
$data = Join-Path $env:USERPROFILE 'UseItUpData'   # outside AppData: store-style Pythons can see a private copy of AppData

$py = (Get-Command py.exe -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python.exe -ErrorAction SilentlyContinue).Source }
if (-not $py) { throw 'Python not found on PATH.' }
$exe = & $py -c "import sys; print(sys.executable)"
$pyw = Join-Path (Split-Path $exe) 'pythonw.exe'
if (-not (Test-Path $pyw)) { throw "pythonw.exe not found next to $exe" }

$script = Join-Path $dir 'sync-server.py'
$vbs = @"
' Use It Up: keeps the pantry sync server running (restarts it 5 s after any exit). Delete this file to stop autostart.
Set sh = CreateObject("WScript.Shell")
Do
  sh.Run """$pyw"" ""$script"" $Port ""$data""", 0, True
  WScript.Sleep 5000
Loop
"@
$startup = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$target = Join-Path $startup 'UseItUp-Sync.vbs'
Set-Content -Path $target -Value $vbs -Encoding ASCII

Get-CimInstance Win32_Process -Filter "Name='wscript.exe'" | Where-Object { $_.CommandLine -match 'UseItUp-Sync' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" | Where-Object { $_.CommandLine -match 'sync-server' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Sleep 1
Start-Process wscript.exe -ArgumentList "`"$target`""
Start-Sleep 3
if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) { "Sync server is listening on 127.0.0.1:$Port" } else { Write-Warning "Sync server did not start" }
