[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "LLM SETUP STOPPED: $Message" -ForegroundColor Red
    exit 1
}

function Read-SecretPlainText([string]$Prompt) {
    $secure = Read-Host $Prompt -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host ""
Write-Host "Sigma Siphon optional OpenAI setup" -ForegroundColor Green
Write-Host ""
Write-Host "This is the ONLY Sigma Siphon setup script that writes SIGMA_LLM_API_KEY."
Write-Host ""

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Fail "Python was not found. Activate the environment where Sigma Siphon is installed."
}

$PythonExe = $python.Source
& $PythonExe -c "import sigma_siphon" 2>$null
if ($LASTEXITCODE -ne 0) {
    Fail (
        "Sigma Siphon is not installed in the currently active Python environment.`n`n" +
        "Install it first with:`n  python -m pip install -e ."
    )
}

$userKey = [Environment]::GetEnvironmentVariable("SIGMA_LLM_API_KEY", "User")
if (-not [string]::IsNullOrWhiteSpace($userKey)) {
    Write-Host "A user-level SIGMA_LLM_API_KEY already exists."
    Write-Host "Its value will not be displayed."
    $replace = Read-Host "Replace it? [y/N]"
    if ($replace -notmatch "^[Yy]") {
        Write-Host "No change made."
        exit 0
    }
}

Write-Host ""
Write-Host "Paste the OpenAI API key when prompted."
Write-Host "Your typing will be hidden."
Write-Host "The key will be stored in your Windows User environment, not in this repository."
Write-Host ""

$apiKey = Read-SecretPlainText "OpenAI API key"
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Fail "No API key was entered."
}

[Environment]::SetEnvironmentVariable("SIGMA_LLM_API_KEY", $apiKey, "User")
$env:SIGMA_LLM_API_KEY = $apiKey
$apiKey = $null

Write-Host ""
Write-Host "API key saved explicitly at your request."
& $PythonExe -m sigma_siphon doctor

Write-Host ""
Write-Host "Close this terminal and open a new PowerShell window."
Write-Host "Then run:"
Write-Host "  sigma-siphon run pasig --llm" -ForegroundColor Yellow
Write-Host ""
