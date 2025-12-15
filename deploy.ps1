# AI Orchestrator - Simple Deployment Script
param(
    [string]$HAHost = "homeassistant.local"
)

$ErrorActionPreference = "Continue"
$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "AI Orchestrator - Deployment Preparation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Create deploy directory
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$deployDir = Join-Path $PROJECT_ROOT "deploy"
$deployPackage = Join-Path $deployDir "ai-orchestrator"

if (Test-Path $deployDir) {
    Remove-Item $deployDir -Recurse -Force
}
New-Item -ItemType Directory -Path $deployPackage -Force | Out-Null

Write-Host "[1/4] Copying project files..." -ForegroundColor Yellow

# Copy essential files
Copy-Item (Join-Path $PROJECT_ROOT "config.yaml") $deployPackage
Copy-Item (Join-Path $PROJECT_ROOT "Dockerfile") $deployPackage
Copy-Item (Join-Path $PROJECT_ROOT "run.sh") $deployPackage
Copy-Item (Join-Path $PROJECT_ROOT "README.md") $deployPackage
Copy-Item (Join-Path $PROJECT_ROOT "DEPLOYMENT.md") $deployPackage

# Copy directories
Copy-Item (Join-Path $PROJECT_ROOT "backend") $deployPackage -Recurse
Copy-Item (Join-Path $PROJECT_ROOT "skills") $deployPackage -Recurse

# Copy built dashboard
$dashboardDist = Join-Path $PROJECT_ROOT "dashboard\dist"
if (Test-Path $dashboardDist) {
    $dashboardDest = Join-Path $deployPackage "dashboard"
    Copy-Item $dashboardDist $dashboardDest -Recurse
    Write-Host "  Dashboard build included" -ForegroundColor Green
}

Write-Host "  Files copied successfully" -ForegroundColor Green

# Create installation guide
Write-Host ""
Write-Host "[2/4] Creating installation guide..." -ForegroundColor Yellow

$guide = @"
AI ORCHESTRATOR - INSTALLATION GUIDE
=====================================

DEPLOYMENT PACKAGE READY!
Location: $deployPackage

QUICK INSTALL STEPS:
-------------------

1. COPY TO HOME ASSISTANT:
   Method A (Samba): Copy this folder to \\$HAHost\addons\
   Method B (SSH): scp -r "$deployPackage" root@${HAHost}:/addons/ai-orchestrator

2. INSTALL ADD-ON:
   - Open Home Assistant web UI
   - Settings -> Add-ons
   - Click ... (three dots) -> Check for updates  
   - Find "AI Orchestrator" under Local add-ons
   - Click and press INSTALL
   - Wait 5-10 minutes for Docker build

3. CONFIGURE (CRITICAL!):
   Before starting, edit configuration:
   
   ollama_host: http://localhost:11434
   dry_run_mode: true
   log_level: info
   heating_model: mistral:7b-instruct
   heating_entities:
     - climate.YOUR_ENTITY_ID_HERE
   decision_interval: 120
   enable_gpu: false

   IMPORTANT: Get your climate entity IDs from:
   Developer Tools -> States -> Filter "climate"

4. START ADD-ON:
   - Click START button
   - Watch Log tab for successful startup

5. ACCESS DASHBOARD:
   http://$HAHost:8099

NEXT STEPS:
- Monitor first decisions (120s interval)
- Verify DRY RUN badge appears
- Confirm no actual temperature changes
- After 24h validation, disable dry_run_mode

See DEPLOYMENT.md for full documentation.
"@

$guide | Out-File (Join-Path $deployPackage "QUICK_START.txt") -Encoding UTF8

Write-Host "  Installation guide created" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "[3/4] Package summary..." -ForegroundColor Yellow
Write-Host "  Location: $deployPackage" -ForegroundColor White
Write-Host "  Size: $((Get-ChildItem $deployPackage -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB) MB" -ForegroundColor White

Write-Host ""
Write-Host "[4/4] Opening deployment folder..." -ForegroundColor Yellow
Start-Process explorer.exe $deployPackage

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " DEPLOYMENT PACKAGE READY!" -ForegroundColor Green  
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Package location:" -ForegroundColor White
Write-Host "  $deployPackage" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next: Copy to Home Assistant and install" -ForegroundColor White
Write-Host "Guide: $deployPackage\QUICK_START.txt" -ForegroundColor White
Write-Host ""
