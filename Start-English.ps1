$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv = Join-Path $root '.venv'
$python = Join-Path $venv 'Scripts\python.exe'
$pythonw = Join-Path $venv 'Scripts\pythonw.exe'
$requirements = Join-Path $root 'requirements.txt'
$stateDir = Join-Path $root '.state'
$statePath = Join-Path $stateDir 'pid.json'
$script = Join-Path $root 'live_overlay_boxes.py'
$terms = Join-Path $root 'overlay_terms.json'

if (-not (Get-Process DoubaoWork -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 })) {
  throw 'Open Doubao Work before starting the English layer.'
}
if (Test-Path -LiteralPath $statePath) {
  $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
  if (Get-Process -Id $state.pid -ErrorAction SilentlyContinue) {
    Write-Output "English layer is already running (PID $($state.pid))."
    exit 0
  }
}

if (-not (Test-Path -LiteralPath $pythonw)) {
  if (Get-Command uv -ErrorAction SilentlyContinue) {
    & uv venv --python 3.12 $venv
  } elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.11 -m venv $venv
  } else {
    & python -m venv $venv
  }
  if ($LASTEXITCODE -ne 0) { throw 'Could not create Python environment.' }
}
$marker = Join-Path $venv '.installed'
$hasher = [System.Security.Cryptography.SHA256]::Create()
try {
  $requirementsHash = [System.BitConverter]::ToString($hasher.ComputeHash([System.IO.File]::ReadAllBytes($requirements))).Replace('-', '')
} finally {
  $hasher.Dispose()
}
$installedHash = ''
if (Test-Path -LiteralPath $marker) {
  $markerContent = Get-Content -LiteralPath $marker -Raw
  if ($null -ne $markerContent) { $installedHash = $markerContent.Trim() }
}
if ($installedHash -ne $requirementsHash) {
  if (Get-Command uv -ErrorAction SilentlyContinue) {
    & uv pip install --python $python -r $requirements
  } else {
    & $python -m pip install -r $requirements
  }
  if ($LASTEXITCODE -ne 0) { throw 'Could not install English layer dependencies.' }
  Set-Content -LiteralPath $marker -Value $requirementsHash -Encoding ascii
}

New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
$stdout = Join-Path $stateDir 'stdout.log'
$stderr = Join-Path $stateDir 'stderr.log'
$arguments = "`"$script`" --terms `"$terms`""
$process = Start-Process -FilePath $pythonw -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
Start-Sleep -Seconds 4
if ($process.HasExited) {
  $errorText = if (Test-Path -LiteralPath $stderr) { Get-Content -LiteralPath $stderr -Tail 15 | Out-String } else { '' }
  throw "English layer exited during startup. $errorText"
}
@{pid=$process.Id; script=$script; started=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
Write-Output "English layer started (PID $($process.Id)). Use Stop-English.ps1 to turn it off."
