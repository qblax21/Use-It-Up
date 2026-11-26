# Use It Up: loads the recipe model into GPU memory at login, and again at set times each day (Windows).
# Run at login by tools\install-preload-autostart.ps1. Manual one-off load:
#   powershell -ExecutionPolicy Bypass -File tools\ollama-preload.ps1 -Once
#
# Why: the models live on D: (a spinning hard disk). Loading qwen2.5:14b from it takes about 2 minutes,
# but once loaded, answers take about 3 seconds. This loads the model before anyone asks.
# NumCtx must match the app's "Context window" setting, or Ollama reloads the model on the first app request.
param(
  [string]$Model = 'qwen2.5:14b',
  [string]$KeepAlive = '4h',        # how long the model stays in GPU memory after the last use (-1 = until reboot)
  [string]$WarmAt = '11:30,16:30',  # also reload it at these times if it was unloaded (before lunch and dinner); '' = off
  [int]$NumCtx = 2048,
  [string]$Ollama = 'http://127.0.0.1:11434',
  [switch]$Once
)
$log = Join-Path $env:LOCALAPPDATA 'UseItUp\preload.log'
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
function Log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Add-Content $log }

function Test-Loaded { try { ((Invoke-RestMethod "$Ollama/api/ps" -TimeoutSec 5).models | Where-Object name -eq $Model) -ne $null } catch { $false } }
function Load-Model {
  $was = Test-Loaded   # still send the request when loaded: it resets the keep-alive timer
  $t = [Diagnostics.Stopwatch]::StartNew()
  try {
    $body = @{ model = $Model; keep_alive = $KeepAlive; options = @{ num_ctx = $NumCtx } } | ConvertTo-Json -Compress
    Invoke-RestMethod "$Ollama/api/generate" -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 900 | Out-Null
    Log ("{0} $Model in {1:N0} s (keep_alive $KeepAlive)" -f $(if ($was) { 'refreshed' } else { 'loaded' }), $t.Elapsed.TotalSeconds)
  } catch { Log "load failed: $($_.Exception.Message)" }
}

# Wait up to 10 minutes for Ollama to start after login.
$up = $false
for ($i = 0; $i -lt 120 -and -not $up; $i++) { try { Invoke-RestMethod "$Ollama/api/version" -TimeoutSec 3 | Out-Null; $up = $true } catch { Start-Sleep 5 } }
if (-not $up) { Log 'Ollama did not start within 10 minutes; giving up'; exit 1 }
Load-Model
if ($Once) { exit 0 }

$slots = @($WarmAt -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$done = @{}
while ($true) {
  Start-Sleep 60
  $now = Get-Date
  foreach ($s in $slots) {
    $at = [datetime]::ParseExact($s, 'H:mm', $null)
    $key = "$($now.ToString('yyyy-MM-dd')) $s"
    if (-not $done[$key] -and $now.TimeOfDay -ge $at.TimeOfDay -and $now.TimeOfDay -lt $at.TimeOfDay.Add([timespan]::FromMinutes(30))) {
      $done[$key] = $true; Load-Model
    }
  }
}
