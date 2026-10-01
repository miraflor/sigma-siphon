[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "SETUP STOPPED: $Message" -ForegroundColor Red
    exit 1
}

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host ""
Write-Host "Sigma Siphon setup" -ForegroundColor Green
Write-Host "Repository: $RepoRoot"
Write-Host ""

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Fail (
        "Python was not found in this terminal.`n`n" +
        "Activate the Python environment you want to use, then rerun this script."
    )
}

$PythonExe = $python.Source
Write-Host "Using the currently active Python:"
Write-Host "  $PythonExe"

$versionOk = & $PythonExe -c "import sys; print(int(sys.version_info >= (3, 11)))"
if ($LASTEXITCODE -ne 0 -or ($versionOk | Select-Object -Last 1).Trim() -ne "1") {
    $version = & $PythonExe --version
    Fail "Sigma Siphon requires Python 3.11 or newer. Current interpreter: $version"
}

# Remove only the obsolete launcher created by an older Sigma Siphon setup.
# This does not touch any Conda/Python environment or any unrelated software.
$LegacyLauncher = Join-Path $env:LOCALAPPDATA "SigmaSiphon\bin\sigma-siphon.cmd"
if (Test-Path $LegacyLauncher) {
    Write-Host ""
    Write-Host "Removing obsolete Sigma Siphon launcher from an older setup..."
    Remove-Item $LegacyLauncher -Force
}

Write-Host ""
Write-Host "Installing Sigma Siphon into the currently active Python environment..."
& $PythonExe -m pip install -e .
if ($LASTEXITCODE -ne 0) {
    Fail "pip could not install Sigma Siphon."
}

Write-Host ""
Write-Host "Running diagnostics..."
& $PythonExe -m sigma_siphon doctor
if ($LASTEXITCODE -ne 0) {
    Fail "Sigma Siphon diagnostics failed."
}

Write-Host ""
Write-Host "SETUP COMPLETE" -ForegroundColor Green
Write-Host ""
Write-Host "Normal use:"
Write-Host "  sigma-siphon run pasig" -ForegroundColor Yellow
Write-Host ""
Write-Host "This setup never reads, creates, copies, saves, or removes an OpenAI API key."
Write-Host "OpenAI is optional. To configure it explicitly later, run:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\setup-llm.ps1"
Write-Host ""
