# Restore the shared pantry from a daily backup (Windows). One command:
#   powershell -ExecutionPolicy Bypass -File tools\restore-pantry.ps1            # newest backup
#   powershell -ExecutionPolicy Bypass -File tools\restore-pantry.ps1 -Date 2026-11-24
#   powershell -ExecutionPolicy Bypass -File tools\restore-pantry.ps1 -List      # show available backups
# The current data is saved first as pre-restore-<time>.zip, so a restore can itself be undone.
# Note: the phones keep their own copies and merge them back in on their next sync. A restore brings back the
# server's copy (for example after the file was lost or damaged); it can't undo a deletion every phone already knows about.
param(
  [string]$Date,
  [switch]$List,
  [string]$DataDir = (Join-Path $env:USERPROFILE 'UseItUpData'),
  [string]$BackupDir = 'D:\UseItUpBackups'
)
$ErrorActionPreference = 'Stop'
$all = @(Get-ChildItem $BackupDir -Filter '*.zip' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
if ($List) { $all | ForEach-Object { '{0}  {1:yyyy-MM-dd HH:mm}  {2:N1} KB' -f $_.Name, $_.LastWriteTime, ($_.Length / 1KB) }; exit 0 }

$daily = @($all | Where-Object Name -match '^pantry-\d{4}-\d\d-\d\d\.zip$' | Sort-Object Name -Descending)
$zip = if ($Date) { $daily | Where-Object Name -eq "pantry-$Date.zip" } else { $daily | Select-Object -First 1 }
if (-not $zip) { throw "No backup found$(if ($Date) { " for $Date" }) in $BackupDir. Use -List to see what's there." }

New-Item -ItemType Directory -Force $DataDir | Out-Null
$current = @(Get-ChildItem $DataDir -Filter *.json -File)
if ($current) {
  $safety = Join-Path $BackupDir ('pre-restore-{0}.zip' -f (Get-Date -Format 'yyyy-MM-dd_HHmmss'))
  Compress-Archive -Path $current.FullName -DestinationPath $safety
  "Saved the current data to $safety"
}

$stage = Join-Path ([IO.Path]::GetTempPath()) ("uiu-restore-" + [guid]::NewGuid())
Expand-Archive $zip.FullName -DestinationPath $stage
try {
  foreach ($f in Get-ChildItem $stage -Filter *.json -File) {
    $null = Get-Content $f.FullName -Raw | ConvertFrom-Json   # refuse to restore a damaged file
    $tmp = Join-Path $DataDir ($f.Name + '.restore')
    Copy-Item $f.FullName $tmp -Force
    Move-Item $tmp (Join-Path $DataDir $f.Name) -Force   # same-folder move: the sync server never sees a half-written file
    "Restored $($f.Name)"
  }
} finally { Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue }
"Done: restored from $($zip.Name). Phones pick it up on their next sync (open the app, or wait up to a minute)."
