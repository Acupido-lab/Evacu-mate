# EvacuMate - Permanent Gateway Boot & Startup Uninstaller

$ErrorActionPreference = "SilentlyContinue"

Write-Host "==========================================================" -ForegroundColor Yellow
Write-Host "  EvacuMate Permanent Gateway - Remove Auto-Boot Setup    " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Yellow
Write-Host ""

# 1. Remove from Startup folder
$StartupFolder = [Environment]::GetFolderPath('Startup')
$StartupLnk = "$StartupFolder\EvacuMate_Permanent_Gateway.lnk"
if (Test-Path $StartupLnk) {
    Remove-Item $StartupLnk -Force
    Write-Host "[SUCCESS] Removed Windows Startup shortcut." -ForegroundColor Green
} else {
    Write-Host "[INFO] Startup shortcut was not present." -ForegroundColor Gray
}

# 2. Unregister Windows Scheduled Task
$TaskName = "EvacuMate_Permanent_Gateway"
try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop | Out-Null
    Write-Host "[SUCCESS] Unregistered Windows Scheduled Task: $TaskName" -ForegroundColor Green
} catch {
    Write-Host "[INFO] Scheduled Task was not present." -ForegroundColor Gray
}

Write-Host ""
Write-Host "Auto-boot has been disabled." -ForegroundColor Green
