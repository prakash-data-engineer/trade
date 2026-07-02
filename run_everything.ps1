$ErrorActionPreference = "Stop"
function Write-Step($msg) { Write-Host "`n==================== $msg ====================" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host $msg -ForegroundColor Green }
function Write-Warn($msg) { Write-Host $msg -ForegroundColor Yellow }

$RepoUrl = "https://github.com/prakash-data-engineer/trade.git"

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot
Write-Step "Working in $ProjectRoot"

if (-not (Test-Path (Join-Path $ProjectRoot "main.py"))) {
    Write-Host "main.py not found in this folder." -ForegroundColor Red
    exit 1
}

Write-Step "Step 1/6: Python virtual environment"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Ok "Created .venv"
} else {
    Write-Ok ".venv already exists"
}
$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$venvPip    = Join-Path $ProjectRoot ".venv\Scripts\pip.exe"

Write-Step "Step 2/6: Installing Python dependencies"
& $venvPip install -r requirements.txt

Write-Step "Step 3/6: Configuring .env"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Warn "Opening Notepad. Fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID, then SAVE and CLOSE Notepad."
    Start-Process notepad ".env" -Wait
} else {
    Write-Ok ".env already exists"
}

Write-Step "Step 4/6: Ollama"
$hasOllama = [bool](Get-Command ollama -ErrorAction SilentlyContinue)
if (-not $hasOllama) {
    Write-Warn "Ollama not found in PATH. Restart PowerShell and re-run this script."
} else {
    Write-Ok "Ollama found"
    $serviceUp = $false
    for ($i = 1; $i -le 10; $i++) {
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
        $model = "llama3.1"
        $envLine = Get-Content ".env" | Where-Object { $_ -match "^OLLAMA_MODEL=" }
        if ($envLine) { $model = ($envLine -split "=", 2)[1].Trim() }
        Write-Step "Pulling model $model"
        ollama pull $model
        Write-Ok "Model ready"
    } else {
        Write-Warn "Could not reach Ollama service. Run ollama serve manually in another window, then re-run."
    }
}

Write-Step "Step 5/6: Running a live test"
& $venvPython main.py

Write-Step "Step 6/6: Pushing code to GitHub"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "git not found. Install from https://git-scm.com/download/win" -ForegroundColor Red
    Start-Process "https://git-scm.com/download/win"
    exit 1
}

if (-not (Select-String -Path ".gitignore" -Pattern "^\.env$" -Quiet -ErrorAction SilentlyContinue)) {
    Add-Content ".gitignore" "`n.env"
}

if (-not (Test-Path ".git")) {
    git init
    git branch -M main
}

if (-not (git config user.name)) {
    $inputName = Read-Host "Enter your name for git commits"
    git config user.name "$inputName"
}
if (-not (git config user.email)) {
    $inputEmail = Read-Host "Enter your email for git commits"
    git config user.email "$inputEmail"
}

$existingRemote = git remote 2>$null
if ($existingRemote -contains "origin") {
    git remote set-url origin $RepoUrl
} else {
    git remote add origin $RepoUrl
}

git add .
git commit -m "Initial commit: NSE trade analyzer end-to-end setup" --allow-empty
Write-Warn "A browser window may open asking you to authorize GitHub."
git push -u origin main

Write-Step "ALL DONE"
Write-Ok "Setup complete and pushed to GitHub."
