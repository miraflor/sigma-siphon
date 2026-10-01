[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "SETUP STOPPED: $Message" -ForegroundColor Red
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
Write-Host "Sigma Siphon one-time setup" -ForegroundColor Green
Write-Host "Repository: $RepoRoot"

Write-Step "Checking Conda"
$conda = Get-Command conda -ErrorAction SilentlyContinue
if (-not $conda) {
    Fail (
        "Conda was not found.`n`n" +
        "Install Miniforge first:`n" +
        "https://github.com/conda-forge/miniforge/releases/latest`n`n" +
        "Choose the Windows x86-64 installer. Then open 'Miniforge Prompt', " +
        "return to this repository, and run:`n`n" +
        "powershell -ExecutionPolicy Bypass -File .\setup.ps1"
    )
}
Write-Host "Conda found."

Write-Step "Creating or updating the isolated sigma-siphon environment"
$envList = (& conda env list --json | ConvertFrom-Json).envs
$existing = $envList | Where-Object {
    (Split-Path $_ -Leaf).ToLowerInvariant() -eq "sigma-siphon"
} | Select-Object -First 1

if ($existing) {
    Write-Host "Existing environment found: $existing"
    & conda env update -n sigma-siphon -f environment.yml --prune
}
else {
    & conda env create -f environment.yml
}
if ($LASTEXITCODE -ne 0) {
    Fail "Conda could not create/update the sigma-siphon environment."
}

Write-Step "Finding the Sigma Siphon Python interpreter"
$pythonLines = & conda run -n sigma-siphon python -c "import sys; print(sys.executable)"
if ($LASTEXITCODE -ne 0) {
    Fail "Could not start Python inside the sigma-siphon environment."
}
$PythonExe = ($pythonLines | Where-Object { $_.Trim() } | Select-Object -Last 1).Trim()
if (-not (Test-Path $PythonExe)) {
    Fail "The environment Python executable could not be located: $PythonExe"
}
Write-Host "Python: $PythonExe"

Write-Step "Optional OpenAI API setup"
$userKey = [Environment]::GetEnvironmentVariable("SIGMA_LLM_API_KEY", "User")
$sessionKey = [Environment]::GetEnvironmentVariable("SIGMA_LLM_API_KEY", "Process")

if (-not [string]::IsNullOrWhiteSpace($userKey)) {
    Write-Host "An OpenAI API key is already installed. It will be kept."
    $env:SIGMA_LLM_API_KEY = $userKey
}
elseif (-not [string]::IsNullOrWhiteSpace($sessionKey)) {
    Write-Host "An OpenAI API key exists in this terminal. Saving it for future sessions."
    [Environment]::SetEnvironmentVariable(
        "SIGMA_LLM_API_KEY",
        $sessionKey,
        "User"
    )
    $env:SIGMA_LLM_API_KEY = $sessionKey
}
else {
    Write-Host ""
    Write-Host "You can test Sigma Siphon for free without an OpenAI API key."
    Write-Host "That test uses deterministic rules only."
    Write-Host ""
    Write-Host "If your OpenAI API account has free/granted credits, you can also"
    Write-Host "test the hosted LLM without paying until those credits are used."
    Write-Host "OpenAI does not guarantee free API credits for every new account."
    Write-Host ""
    $choice = Read-Host "Set up an OpenAI API key now? [y/N]"
    if ($choice -match "^[Yy]") {
        Write-Host ""
        Write-Host "The key will NOT be written into this repository."
        Write-Host "Your typing will be hidden."
        Write-Host ""
        $apiKey = Read-SecretPlainText "Paste your OpenAI API key"
        if ([string]::IsNullOrWhiteSpace($apiKey)) {
            Write-Host "No key entered. Continuing with rules-only testing." -ForegroundColor Yellow
        }
        else {
            [Environment]::SetEnvironmentVariable(
                "SIGMA_LLM_API_KEY",
                $apiKey,
                "User"
            )
            $env:SIGMA_LLM_API_KEY = $apiKey
            $apiKey = $null
            Write-Host "API key saved to your Windows user environment."
        }
    }
    else {
        Write-Host "Skipping OpenAI API setup. You can add it later by rerunning setup.ps1."
    }
}

Write-Step "Creating the permanent sigma-siphon command"
$LauncherDir = Join-Path $env:LOCALAPPDATA "SigmaSiphon\bin"
New-Item -ItemType Directory -Force -Path $LauncherDir | Out-Null
$LauncherPath = Join-Path $LauncherDir "sigma-siphon.cmd"

$launcherLines = @(
    "@echo off",
    "cd /d `"$RepoRoot`"",
    "`"$PythonExe`" -m sigma_siphon %*"
)
Set-Content -Path $LauncherPath -Value $launcherLines -Encoding ASCII

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathParts = @()
if (-not [string]::IsNullOrWhiteSpace($userPath)) {
    $pathParts = $userPath.Split(";") | Where-Object { $_ }
}
$alreadyOnPath = $pathParts | Where-Object {
    $_.TrimEnd("\") -ieq $LauncherDir.TrimEnd("\")
}
if (-not $alreadyOnPath) {
    $newUserPath = if ([string]::IsNullOrWhiteSpace($userPath)) {
        $LauncherDir
    }
    else {
        "$userPath;$LauncherDir"
    }
    [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
}

$currentPathParts = $env:Path.Split(";")
if (-not ($currentPathParts | Where-Object { $_ -ieq $LauncherDir })) {
    $env:Path = "$LauncherDir;$env:Path"
}

Write-Host "Launcher: $LauncherPath"

Write-Step "Running Sigma Siphon diagnostics"
& $PythonExe -m sigma_siphon doctor
if ($LASTEXITCODE -ne 0) {
    Fail "Sigma Siphon diagnostics failed."
}

Write-Host ""
Write-Host "SETUP COMPLETE" -ForegroundColor Green
Write-Host ""
Write-Host "Close this terminal and open a NEW PowerShell window."
Write-Host ""

$finalKey = [Environment]::GetEnvironmentVariable("SIGMA_LLM_API_KEY", "User")
if (-not [string]::IsNullOrWhiteSpace($finalKey)) {
    Write-Host "OpenAI API key: configured"
    Write-Host "Run the normal hybrid pipeline with:"
    Write-Host ""
    Write-Host "    sigma-siphon run pasig" -ForegroundColor Yellow
}
else {
    Write-Host "OpenAI API key: not configured"
    Write-Host "Run the completely free rules-only test with:"
    Write-Host ""
    Write-Host "    sigma-siphon run pasig --no-llm" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "When you want LLM classification, rerun setup.ps1 and add an API key."
}
Write-Host ""
