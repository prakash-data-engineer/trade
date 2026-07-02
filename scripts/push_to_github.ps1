<#
.SYNOPSIS
    Initializes git in this project (if needed) and pushes it to your GitHub repo.

.USAGE
    powershell -ExecutionPolicy Bypass -File .\scripts\push_to_github.ps1 -RepoUrl "https://github.com/prakash-data-engineer/nse-trade-analyzer.git"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$RepoUrl
)

$ErrorActionPreference = "Stop"
function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host $msg -ForegroundColor Green }

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# --- Check git is installed ---
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "git is not installed. Install it from https://git-scm.com/download/win, then re-run this script." -ForegroundColor Red
    Start-Process "https://git-scm.com/download/win"
    exit 1
}

# --- Safety check: make sure .env is not about to be committed ---
if (-not (Select-String -Path ".gitignore" -Pattern "^\.env$" -Quiet -ErrorAction SilentlyContinue)) {
    Add-Content ".gitignore" "`n.env"
    Write-Host "Added .env to .gitignore for safety (it holds your Telegram token)." -ForegroundColor Yellow
}

# --- Init repo if needed ---
if (-not (Test-Path ".git")) {
    Write-Step "Initializing git repository"
    git init
    git branch -M main
} else {
    Write-Ok "Git repo already initialized"
}

# --- Configure identity if not already set globally ---
$userName = git config user.name
$userEmail = git config user.email
if (-not $userName) {
    $inputName = Read-Host "Enter your name for git commits"
    git config user.name "$inputName"
}
if (-not $userEmail) {
    $inputEmail = Read-Host "Enter your email for git commits"
    git config user.email "$inputEmail"
}

# --- Add remote ---
$existingRemote = git remote 2>$null
if ($existingRemote -contains "origin") {
    Write-Step "Updating existing 'origin' remote to $RepoUrl"
    git remote set-url origin $RepoUrl
} else {
    Write-Step "Adding remote 'origin' -> $RepoUrl"
    git remote add origin $RepoUrl
}

# --- Commit and push ---
Write-Step "Staging and committing files"
git add .
git commit -m "Initial commit: NSE trade analyzer end-to-end setup" --allow-empty

Write-Step "Pushing to GitHub (you'll be prompted to log in via browser on first push)"
git push -u origin main

Write-Ok "Done! Your code is now on GitHub at: $($RepoUrl -replace '\.git$','')"
