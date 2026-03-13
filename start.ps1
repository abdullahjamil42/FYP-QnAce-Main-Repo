<# 
  Q&Ace — Project Startup Script
  
  Usage:  .\start.ps1
  
  Starts both backend (FastAPI on :8000) and frontend (Next.js on :3000).
  Press Ctrl+C to stop the frontend; the backend runs in a background job.
#>

$ErrorActionPreference = "Continue"
$root = $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Q&Ace — Starting Project" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Kill any existing processes on ports 3000 / 8000 ──
foreach ($port in @(3000, 8000)) {
    $pids = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        Where-Object { $_ -ne 0 }
    foreach ($p in $pids) {
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        Write-Host "  Killed old process on port $port (PID $p)" -ForegroundColor Yellow
    }
}

# ── 2. Clear stale .next cache (prevents 'Cannot find module' errors) ──
$nextDir = Join-Path $root "client\.next"
if (Test-Path $nextDir) {
    Remove-Item -Recurse -Force $nextDir
    Write-Host "  Cleared stale .next cache" -ForegroundColor Yellow
}

# ── 3. Start Backend (FastAPI + Whisper) ──
Write-Host ""
Write-Host "[Backend] Starting on http://127.0.0.1:8000 ..." -ForegroundColor Green
$backendJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location (Join-Path $root "server")
    & (Join-Path $root ".venv311\Scripts\python.exe") -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info 2>&1
} -ArgumentList $root
Write-Host "  Backend started (Job ID: $($backendJob.Id))" -ForegroundColor DarkGray

# ── 4. Wait for backend health ──
Write-Host "[Backend] Waiting for health check (models loading) ..." -ForegroundColor Green
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 3
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2
        $body = $r.Content | ConvertFrom-Json
        $whisper = $body.models.whisper
        Write-Host "  Backend UP — Whisper: $whisper" -ForegroundColor Green
        $ready = $true
        break
    } catch {
        Write-Host "  ... still loading ($($i * 3)s)" -ForegroundColor DarkGray
    }
}
if (-not $ready) {
    Write-Host "  WARNING: Backend did not become healthy in 180s" -ForegroundColor Red
}

# ── 5. Start Frontend (Next.js) ──
Write-Host ""
Write-Host "[Frontend] Starting on http://127.0.0.1:3000 ..." -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Open http://localhost:3000 in your browser" -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location (Join-Path $root "client")
try {
    npm run dev -- --hostname 127.0.0.1 --port 3000
} finally {
    # Cleanup: stop backend when frontend stops
    Write-Host ""
    Write-Host "Stopping backend ..." -ForegroundColor Yellow
    Stop-Job -Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $backendJob -Force -ErrorAction SilentlyContinue
    
    $pids = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        Where-Object { $_ -ne 0 }
    foreach ($p in $pids) {
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Done." -ForegroundColor Green
}
