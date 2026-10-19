$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$statePath = Join-Path $root '.state\pid.json'
$script = Join-Path $root 'live_overlay_boxes.py'
if (-not (Test-Path -LiteralPath $statePath)) {
  Write-Output 'English layer is not running.'
  exit 0
}
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$running = Get-CimInstance Win32_Process -Filter "ProcessId=$($state.pid)" -ErrorAction SilentlyContinue
if ($running -and $running.CommandLine -and $running.CommandLine.Contains($script)) {
  Stop-Process -Id $state.pid -Force
}
Remove-Item -LiteralPath $statePath
Write-Output 'English layer stopped. Doubao Work was not changed.'
