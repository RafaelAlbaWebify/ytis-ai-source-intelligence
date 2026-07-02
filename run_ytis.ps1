$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "Stopping any old YTIS app processes..." -ForegroundColor Cyan
$ytisProcesses = Get-CimInstance Win32_Process |
Where-Object {
    $_.Name -match "python" -and
    $_.CommandLine -match "ytis\.app"
}

foreach ($p in $ytisProcesses) {
    Write-Host "Stopping old YTIS PID $($p.ProcessId)" -ForegroundColor Yellow
    Stop-Process -Id $p.ProcessId -Force
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
}

Write-Host "Installing/updating dependencies..." -ForegroundColor Cyan
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt

$env:PYTHONPATH = Join-Path $ProjectRoot "src"

Write-Host "Starting YTIS..." -ForegroundColor Green
& $VenvPython -m ytis.app
