<#
.SYNOPSIS
    End-to-end Ollama setup for the NSE Trade Analyzer (Windows PowerShell).

.DESCRIPTION
    1. Checks if Ollama is already installed.
    2. Installs it via winget if missing (falls back to manual instructions).
    3. Waits for the Ollama service to come up on localhost:11434.
    4. Pulls the model specified in .env (or defaults to llama3.1).
    5. Runs a one-line test prompt to confirm everything works.

.USAGE
    Right-click this file -> "Run with PowerShell"
    OR from a PowerShell terminal in the project folder:
        .\scripts\setup_ollama.ps1
#>

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

function Test-OllamaInstalled {
    return [bool](Get-Command ollama -ErrorAction SilentlyContinue)
}

function Test-OllamaServiceUp {
    try {
        Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null
        return $true
    } catch {
        return $false
    }
}

# --- 1. Check / install Ollama ---
Write-Step "Checking for Ollama installation"

if (Test-OllamaInstalled) {
    Write-Host "Ollama is already installed." -ForegroundColor Green
} else {
    Write-Host "Ollama not found." -ForegroundColor Yellow

    $hasWinget = [bool](Get-Command winget -ErrorAction SilentlyContinue)
    if ($hasWinget) {
        Write-Step "Installing Ollama via winget (this may take a few minutes)"
        winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
    } else {
        Write-Host "winget not available on this system." -ForegroundColor Red
        Write-Host "Please install manually:" -ForegroundColor Yellow
        Write-Host "  1. Open https://ollama.com/download in your browser"
        Write-Host "  2. Download and run the Windows installer"
        Write-Host "  3. Re-run this script afterward"
        Start-Process "https://ollama.com/download"
        exit 1
    }

    Write-Host "Re-checking installation..."
    Start-Sleep -Seconds 5
    if (-not (Test-OllamaInstalled)) {
        Write-Host "Ollama command still not found. You may need to restart your terminal/VS Code" -ForegroundColor Red
        Write-Host "(or your PC) so PATH updates take effect, then re-run this script." -ForegroundColor Red
        exit 1
    }
}

# --- 2. Wait for the background service to be reachable ---
Write-Step "Waiting for Ollama service on http://localhost:11434"

$maxAttempts = 15
$attempt = 0
$serviceUp = $false

while ($attempt -lt $maxAttempts -and -not $serviceUp) {
    $attempt++
    if (Test-OllamaServiceUp) {
        $serviceUp = $true
        break
    }
    Write-Host "  ...not up yet (attempt $attempt/$maxAttempts), trying 'ollama serve' in background"
    if ($attempt -eq 1) {
        # Ollama normally auto-starts as a service after install; if not, start it manually.
        Start-Process -WindowStyle Hidden -FilePath "ollama" -ArgumentList "serve"
    }
    Start-Sleep -Seconds 3
}

if (-not $serviceUp) {
    Write-Host "Could not reach Ollama service after $maxAttempts attempts." -ForegroundColor Red
    Write-Host "Try opening a terminal and running 'ollama serve' manually, then re-run this script." -ForegroundColor Red
    exit 1
}

Write-Host "Ollama service is up." -ForegroundColor Green

# --- 3. Determine which model to pull (reads .env if present) ---
Write-Step "Determining model to pull"

$model = "llama3.1"
$envPath = Join-Path $PSScriptRoot "..\.env"
if (Test-Path $envPath) {
    $line = Get-Content $envPath | Where-Object { $_ -match "^OLLAMA_MODEL=" }
    if ($line) {
        $model = ($line -split "=", 2)[1].Trim()
    }
}
Write-Host "Model: $model"

# --- 4. Pull the model ---
Write-Step "Pulling model '$model' (this can take a while on first run, several GB download)"
ollama pull $model

# --- 5. Test it ---
Write-Step "Running test prompt"
$testOutput = ollama run $model "Reply with exactly: Ollama setup OK" 2>&1
Write-Host $testOutput

Write-Step "Done"
Write-Host "Ollama is installed, running, and model '$model' is ready." -ForegroundColor Green
Write-Host "Make sure .env has:  OLLAMA_MODEL=$model  and  USE_OLLAMA=true"
Write-Host "Now test the full pipeline with:  python main.py"
