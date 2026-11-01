$host.UI.RawUI.WindowTitle = "FDR SmartTrack MVP Launcher"
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  🏛  FDR SmartTrack Portal — SIH 26265 MVP Launcher" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$portalDir = if (Test-Path "$baseDir\fdr-portal") { "$baseDir\fdr-portal" } else { $baseDir }

Write-Host "Starting Backend (FastAPI on http://127.0.0.1:8000)..." -ForegroundColor Green
Start-Process cmd.exe -ArgumentList "/k", "call `"$portalDir\backend\run_backend.bat`""

Write-Host "Starting Frontend (Vite on http://localhost:5173)..." -ForegroundColor Green
Start-Process cmd.exe -ArgumentList "/k", "call `"$portalDir\frontend\run_frontend.bat`""

Start-Sleep -Seconds 3
Write-Host "Opening browser at http://localhost:5173 ..." -ForegroundColor Yellow
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "Demo Accounts (Password for all: Demo@123):" -ForegroundColor White
Write-Host "  • Super Admin:          superadmin@demo.in" -ForegroundColor Gray
Write-Host "  • Finance Officer:      finance@inst001.demo.in" -ForegroundColor Gray
Write-Host "  • Institution Reviewer: reviewer@inst001.demo.in" -ForegroundColor Gray
Write-Host "  • AICTE Officer:        aicte@demo.in" -ForegroundColor Gray
Write-Host "  • Auditor:              auditor@demo.in" -ForegroundColor Gray
Write-Host ""

