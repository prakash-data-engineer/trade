<#
.SYNOPSIS
    ONE script to set up everything: Python venv, dependencies, .env file,
    Ollama + model, and a test run of the analyzer.

.USAGE
    Run this exact command from the project folder (bypasses the PowerShell
    script-execution restriction for just this one run, nothing permanent):

        powershell -ExecutionPolicy Bypass -File .\scripts\setup_all.ps1
#>

$ErrorActionPreference = "Stop"
function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host $msg -ForegroundColor Green }
function Write-Warn($msg) { Write-Host $msg -ForegroundColor Yellow }

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
Write-Step "Working in $ProjectRoot"

# --- 1. Python venv (no Activate.ps1 needed — we call venv's python/pip directly) ---
Write-Step "Creating virtual environment (.venv) if missing"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Ok "Created .venv"
} else {
    Write-Ok ".venv already exists"
}
$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$venvPip    = Join-Path $ProjectRoot ".venv\Scripts\pip.exe"

# --- 2. Install dependencies ---
Write-Step "Installing Python dependencies"
& $venvPip install -r requirements.txt

# --- 3. .env file ---
Write-Step "Setting up .env"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Warn "Created .env from template. Opening Notepad — fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID, then SAVE and CLOSE Notepad to continue."
    Start-Process notepad ".env" -Wait
} else {
    Write-Ok ".env already exists, leaving as-is"
}

# --- 4. Ollama install + model pull ---
Write-Step "Checking Ollama"
$hasOllama = [bool](Get-Command ollama -ErrorAction SilentlyContinue)

if (-not $hasOllama) {
    $hasWinget = [bool](Get-Command winget -ErrorAction SilentlyContinue)
    if ($hasWinget) {
        Write-Step "Installing Ollama via winget"
        winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
        Start-Sleep -Seconds 5
    } else {
        Write-Warn "winget not found. Opening the Ollama download page — please install it manually, then re-run this script."
        Start-Process "https://ollama.com/download"
        exit 1
    }
}

# Refresh PATH in this session in case Ollama was just installed
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Step "Waiting for Ollama service (localhost:11434)"
$serviceUp = $false
for ($i = 1; $i -le 15; $i++) {
    try {
        Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null
        $serviceUp = $true
        break
    } catch {
        if ($i -eq 1) { Start-Process -WindowStyle Hidden -FilePath "ollama" -ArgumentList "serve" -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 3
    }
}
if ($serviceUp) {
    Write-Ok "Ollama service is up"

    $model = "llama3.1"
    $envLine = Get-Content ".env" | Where-Object { $_ -match "^OLLAMA_MODEL=" }
    if ($envLine) { $model = ($envLine -split "=", 2)[1].Trim() }

    Write-Step "Pulling model '$model' (large download on first run — be patient)"
    ollama pull $model
    Write-Ok "Model ready"
} else {
    Write-Warn "Could not reach Ollama service. Skipping model pull — you can run scripts\setup_ollama.ps1 later, or set USE_OLLAMA=false in .env to skip LLM notes entirely."
}

# --- 5. Test run ---
Write-Step "Running a test cycle: python main.py"
& $venvPython main.py

Write-Step "Setup complete"
Write-Ok "If you saw analysis output above (and a Telegram message), you're fully set up."
Write-Host "To run it manually again later:  .venv\Scripts\python.exe main.py"
Write-Host "To schedule it every 5 min, see the Task Scheduler section in README.md"
