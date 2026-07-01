$ErrorActionPreference = "Stop"

Write-Host "Stopping all running YTIS app processes..." -ForegroundColor Cyan

$ytisProcesses = Get-CimInstance Win32_Process |
Where-Object {
    $_.Name -match "python" -and
    $_.CommandLine -match "ytis\.app"
}

if (-not $ytisProcesses) {
    Write-Host "No YTIS app processes found." -ForegroundColor Yellow
    exit 0
}

foreach ($p in $ytisProcesses) {
    Write-Host "Stopping PID $($p.ProcessId): $($p.CommandLine)" -ForegroundColor Yellow
    Stop-Process -Id $p.ProcessId -Force
}

Write-Host "Done." -ForegroundColor Green
