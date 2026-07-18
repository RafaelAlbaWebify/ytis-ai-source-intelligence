[CmdletBinding()]
param(
    [switch]$SkipDependencyInstall,
    [switch]$SkipBrowser,
    [switch]$AllowOtherBranch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory)][string]$Label,
        [Parameter(Mandatory)][scriptblock]$Action
    )
    Write-Step $Label
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE."
    }
}

$scriptPath = $MyInvocation.MyCommand.Path
if (-not $scriptPath) {
    throw 'This validator must be executed from its saved .ps1 file.'
}
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not (Test-Path (Join-Path $repoRoot '.git'))) {
    throw "Repository root was not found at $repoRoot."
}

$branch = (& git -C $repoRoot branch --show-current).Trim()
$commit = (& git -C $repoRoot rev-parse HEAD).Trim()
if (-not $branch -or -not $commit) {
    throw 'Unable to resolve the current Git branch and commit.'
}
if (-not $AllowOtherBranch -and $branch -ne 'integration/roadmap-87') {
    throw "Expected branch integration/roadmap-87, but the current branch is $branch. No checkout or update was performed."
}

$dirty = @(& git -C $repoRoot status --porcelain --untracked-files=all)
if ($dirty.Count -gt 0) {
    Write-Host ($dirty -join [Environment]::NewLine) -ForegroundColor Yellow
    throw 'The repository has uncommitted or untracked changes. Validation stopped without modifying the checkout.'
}

try {
    $listener = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        throw 'TCP port 8080 is already in use. Stop the existing process before running release validation.'
    }
} catch [Microsoft.PowerShell.Commands.WriteErrorException] {
    throw
} catch {
    # Get-NetTCPConnection is not available on every Windows edition. The browser tests will report a port conflict if present.
}

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$tempRoot = Join-Path $env:TEMP "YTIS_RELEASE_VALIDATION_$stamp"
$venvRoot = Join-Path $tempRoot 'venv'
$runRoot = Join-Path $tempRoot 'review'
$logsRoot = Join-Path $runRoot 'logs'
$evidenceRoot = Join-Path $runRoot 'artifacts'
New-Item -ItemType Directory -Force -Path $logsRoot, $evidenceRoot | Out-Null

$downloads = Join-Path $env:USERPROFILE 'Downloads'
if (-not (Test-Path $downloads)) {
    New-Item -ItemType Directory -Force -Path $downloads | Out-Null
}
$zipPath = Join-Path $downloads "YTIS_RELEASE_VALIDATION_${stamp}_${commit.Substring(0, 8)}.zip"

$summary = [ordered]@{
    project = 'YTIS - AI Source Intelligence'
    generated_at = (Get-Date).ToString('o')
    repository_root = $repoRoot
    branch = $branch
    commit = $commit
    python = $null
    dependency_install_skipped = [bool]$SkipDependencyInstall
    browser_validation_skipped = [bool]$SkipBrowser
    smoke_tests = @()
    browser_tests = @()
    passed = $false
}

try {
    Write-Step 'Create isolated Python 3.12 environment'
    & py -3.12 -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) {
        throw 'Python 3.12 is required. Install it or make it available through the Windows py launcher.'
    }
    $python = Join-Path $venvRoot 'Scripts\python.exe'
    if (-not (Test-Path $python)) {
        throw "Virtual-environment Python was not created at $python."
    }
    $summary.python = (& $python --version 2>&1 | Out-String).Trim()

    if (-not $SkipDependencyInstall) {
        Invoke-Checked 'Install YTIS release-validation dependencies' {
            & $python -m pip install --upgrade pip setuptools wheel
            if ($LASTEXITCODE -ne 0) { return }
            & $python -m pip install -r (Join-Path $repoRoot 'requirements-dev.txt')
        }
        if (-not $SkipBrowser) {
            Invoke-Checked 'Install Playwright Chromium' {
                & $python -m playwright install chromium
            }
        }
    }

    $env:PYTHONPATH = Join-Path $repoRoot 'src'
    $env:PYTHONUNBUFFERED = '1'

    $repoArtifacts = Join-Path $repoRoot 'artifacts'
    if (Test-Path $repoArtifacts) {
        Remove-Item -Recurse -Force $repoArtifacts
    }
    New-Item -ItemType Directory -Force -Path $repoArtifacts | Out-Null

    $smokeTests = Get-ChildItem -Path (Join-Path $repoRoot 'tools') -File -Filter '*_smoke.py' |
        Sort-Object Name
    foreach ($test in $smokeTests) {
        $logPath = Join-Path $logsRoot ("smoke_{0}.log" -f $test.BaseName)
        Write-Step "Smoke proof: $($test.Name)"
        Push-Location $repoRoot
        try {
            & $python $test.FullName *>&1 | Tee-Object -FilePath $logPath
            $exitCode = $LASTEXITCODE
        } finally {
            Pop-Location
        }
        $summary.smoke_tests += [ordered]@{
            name = $test.Name
            exit_code = $exitCode
            passed = ($exitCode -eq 0)
            log = "logs/$([IO.Path]::GetFileName($logPath))"
        }
    }

    if (-not $SkipBrowser) {
        $browserTests = Get-ChildItem -Path (Join-Path $repoRoot 'tools') -File -Filter 'playwright_*.py' |
            Sort-Object Name
        foreach ($test in $browserTests) {
            $logPath = Join-Path $logsRoot ("browser_{0}.log" -f $test.BaseName)
            Write-Step "Browser journey: $($test.Name)"
            Push-Location $repoRoot
            try {
                & $python $test.FullName *>&1 | Tee-Object -FilePath $logPath
                $exitCode = $LASTEXITCODE
            } finally {
                Pop-Location
            }
            $summary.browser_tests += [ordered]@{
                name = $test.Name
                exit_code = $exitCode
                passed = ($exitCode -eq 0)
                log = "logs/$([IO.Path]::GetFileName($logPath))"
            }
        }
    }

    if (Test-Path $repoArtifacts) {
        Copy-Item -Path (Join-Path $repoArtifacts '*') -Destination $evidenceRoot -Recurse -Force -ErrorAction SilentlyContinue
    }

    $smokePassed = @($summary.smoke_tests | Where-Object { -not $_.passed }).Count -eq 0
    $browserPassed = $SkipBrowser -or (@($summary.browser_tests | Where-Object { -not $_.passed }).Count -eq 0)
    $summary.passed = $smokePassed -and $browserPassed

    $summaryPath = Join-Path $runRoot 'release-validation.json'
    $summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryPath -Encoding UTF8

    $readme = @"
# YTIS local release-validation evidence

- Branch: `$branch`
- Commit: `$commit`
- Generated: $($summary.generated_at)
- Python: $($summary.python)
- Smoke proofs passed: $(@($summary.smoke_tests | Where-Object passed).Count) / $($summary.smoke_tests.Count)
- Browser journeys passed: $(@($summary.browser_tests | Where-Object passed).Count) / $($summary.browser_tests.Count)
- Overall result: $(if ($summary.passed) { 'PASS' } else { 'FAIL' })

The `artifacts` directory contains screenshots, traces, server logs and structured reports produced by the repository's own validation tools. The `logs` directory contains one console log per proof.

This package validates the exact commit above. It does not modify, commit, merge, pull or switch the repository.
"@
    Set-Content -Path (Join-Path $runRoot 'README.md') -Value $readme -Encoding UTF8

    if (Test-Path $zipPath) {
        Remove-Item -Force $zipPath
    }
    Compress-Archive -Path (Join-Path $runRoot '*') -DestinationPath $zipPath -CompressionLevel Optimal

    Write-Host "`nValidation package: $zipPath" -ForegroundColor Green
    Write-Host "Overall result: $(if ($summary.passed) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($summary.passed) { 'Green' } else { 'Red' })
    if (-not $summary.passed) {
        exit 1
    }
} finally {
    Remove-Item -Recurse -Force $tempRoot -ErrorAction SilentlyContinue
}
