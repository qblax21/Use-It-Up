# Installs the Ollama Host-header proxy so it starts at login and restarts itself if it ever stops (Windows).
#   powershell -ExecutionPolicy Bypass -File tools\install-proxy-autostart.ps1 [-ListenPort 11436] [-OllamaPort 11434]
# - Copies ollama-proxy.py to %USERPROFILE%\UseItUp (C:, so it doesn't depend on another drive being ready at login; not under AppData, which some sandboxed apps see a private copy of)
# - Writes a tiny supervisor .vbs into your Startup folder (delete UseItUp-Ollama-Proxy.vbs to remove autostart)
param([int]$ListenPort = 11436, [int]$OllamaPort = 11434)
$ErrorActionPreference = 'Stop'

$dir = Join-Path $env:USERPROFILE 'UseItUp'
New-Item -ItemType Directory -Force $dir | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'ollama-proxy.py') (Join-Path $dir 'ollama-proxy.py') -Force

# find pythonw.exe next to the Python that "py" / "python" resolves to
$py = (Get-Command py.exe -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python.exe -ErrorAction SilentlyContinue).Source }
if (-not $py) { throw 'Python not found on PATH.' }
$exe = & $py -c "import sys; print(sys.executable)"
$pyw = Join-Path (Split-Path $exe) 'pythonw.exe'
if (-not (Test-Path $pyw)) { throw "pythonw.exe not found next to $exe" }

$script = Join-Path $dir 'ollama-proxy.py'
$vbs = @"
' Use It Up: keeps the loopback-only Ollama proxy running (restarts it 5 s after any exit). Delete this file to stop autostart.
Set sh = CreateObject("WScript.Shell")
Do
  sh.Run """$pyw"" ""$script"" $ListenPort $OllamaPort", 0, True
  WScript.Sleep 5000
Loop
"@
$startup = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$target = Join-Path $startup 'UseItUp-Ollama-Proxy.vbs'
Set-Content -Path $target -Value $vbs -Encoding ASCII

# (re)start it now
Get-CimInstance Win32_Process -Filter "Name='wscript.exe'" | Where-Object { $_.CommandLine -match 'UseItUp-Ollama-Proxy' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" | Where-Object { $_.CommandLine -match 'ollama-proxy' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Sleep 1
Start-Process wscript.exe -ArgumentList "`"$target`""
Start-Sleep 3
if (Get-NetTCPConnection -State Listen -LocalPort $ListenPort -ErrorAction SilentlyContinue) { "Proxy is listening on 127.0.0.1:$ListenPort" } else { Write-Warning "Proxy did not start" }
