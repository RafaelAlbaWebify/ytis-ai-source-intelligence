# Local Windows release validation

This workflow produces real YTIS browser screenshots and validation evidence on a Windows workstation when GitHub-hosted runners are unavailable.

It is a diagnostic and visual-review path. It does not replace the final Windows/Linux GitHub Actions release gate.

## Validator

Use `scripts/Run-YTIS-Release-Validation.ps1` from the repository.

The script:

- locates the repository from its own saved path;
- requires the `integration/roadmap-87` branch by default;
- stops before making changes when tracked or untracked files are present;
- never pulls, switches branches, commits, merges or overwrites source files;
- uses a temporary Python 3.12 virtual environment outside the repository;
- runs the exact Baseline CI Python commands in workflow order;
- runs every repository Playwright browser journey;
- captures real screenshots, traces, server logs and structured reports;
- removes generated repository artifacts after copying the evidence;
- creates one timestamped ZIP directly in Downloads;
- does not open Downloads automatically.

## Prerequisites

- Windows PowerShell or PowerShell 7;
- Git on PATH;
- Python 3.12 available through the Windows Python launcher;
- internet access for the first dependency and Chromium installation;
- TCP port 8080 free.

## Evidence package

The resulting ZIP contains:

- a README with branch, exact commit and pass totals;
- a JSON manifest with every command and exit code;
- one console log per proof;
- repository-generated screenshots, traces, server logs and JSON reports.

A failing proof does not prevent later proofs from running. The final ZIP is still created so the failure can be diagnosed from evidence.

## Review sequence

1. Run the validator from the checked-out release branch.
2. Upload the generated ZIP for review.
3. Inspect the Start Here screenshot first, then every other browser screenshot and report.
4. Correct real failures from the included logs.
5. Repeat on the corrected exact commit.
6. Once GitHub-hosted runners are restored, rerun the complete Windows/Linux and browser matrix before merging PR #23.
