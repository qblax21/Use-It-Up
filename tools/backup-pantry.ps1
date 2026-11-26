# Daily backup of the shared-pantry data (Windows). Keeps the newest 14 days.
#   powershell -ExecutionPolicy Bypass -File tools\backup-pantry.ps1 [-DataDir ...] [-BackupDir ...] [-Keep 14]
# Run daily by the "UseItUp pantry backup" scheduled task (tools\install-backup-task.ps1).
# Backups go to D: by default: a different physical disk from the data on C:, so one disk failing can't lose both.
param(
  [string]$DataDir = (Join-Path $env:USERPROFILE 'UseItUpData'),
  [string]$BackupDir = 'D:\UseItUpBackups',
  [int]$Keep = 14
)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force $BackupDir | Out-Null
$files = @(Get-ChildItem $DataDir -Filter *.json -File)   # skip *.json.tmp files the server may be writing
if (-not $files) { Write-Warning "No pantry files in $DataDir; nothing to back up."; exit 0 }

$name = 'pantry-{0}.zip' -f (Get-Date -Format 'yyyy-MM-dd')   # one per day: running it again the same day replaces it
$tmp = Join-Path $BackupDir "$name.partial"
$stage = Join-Path ([IO.Path]::GetTempPath()) ("uiu-backup-" + [guid]::NewGuid())
New-Item -ItemType Directory $stage | Out-Null
try {
  $files | Copy-Item -Destination $stage   # copy first so a write by the server during zipping can't produce a torn file
  if (Test-Path "$tmp.zip") { Remove-Item "$tmp.zip" -Force }
  Compress-Archive -Path (Join-Path $stage '*') -DestinationPath "$tmp.zip"
  Move-Item "$tmp.zip" (Join-Path $BackupDir $name) -Force
} finally { Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue }

# Rotate: keep the newest $Keep daily backups (pre-restore safety copies are kept separately, newest 5).
Get-ChildItem $BackupDir -Filter 'pantry-????-??-??.zip' | Sort-Object Name -Descending | Select-Object -Skip $Keep | Remove-Item -Force
Get-ChildItem $BackupDir -Filter 'pre-restore-*.zip' | Sort-Object Name -Descending | Select-Object -Skip 5 | Remove-Item -Force
"Backed up $($files.Count) pantry file(s) to $(Join-Path $BackupDir $name)"
