# EvacuMate - Permanent Gateway Boot & Startup Auto-Reconnect Installer
# Ensures the gateway auto-reconnects to the permanent link on every reboot/boot.

$ErrorActionPreference = "SilentlyContinue"
$ProjectDir = $PSScriptRoot
if (-not $ProjectDir) {
    $ProjectDir = "c:\Users\ryuki a acupido\OneDrive\Desktop\System_GrpProject(IT ELEC),"
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  EvacuMate Permanent Gateway - Boot Auto-Start Setup     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$WshShell = New-Object -ComObject WScript.Shell

# 1. Install to User Startup Folder (Guaranteed, zero admin prompt required)
$StartupFolder = [Environment]::GetFolderPath('Startup')
$StartupLnk = "$StartupFolder\EvacuMate_Permanent_Gateway.lnk"

$Shortcut = $WshShell.CreateShortcut($StartupLnk)
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = "`"$ProjectDir\run_gateway_silent.vbs`""
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.Description = "EvacuMate Permanent Public Online Runtime Gateway (Auto-start on boot)"
$Shortcut.IconLocation = "$ProjectDir\bin\ngrok.exe,0"
$Shortcut.Save()

if (Test-Path $StartupLnk) {
    Write-Host "[SUCCESS] Added to Windows Startup folder:" -ForegroundColor Green
    Write-Host "          $StartupLnk" -ForegroundColor Gray
} else {
    Write-Host "[WARNING] Could not create startup folder shortcut." -ForegroundColor Yellow
}

# 2. Register Windows Scheduled Task (For system-level persistence)
$TaskName = "EvacuMate_Permanent_Gateway"
try {
    $Action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$ProjectDir\run_gateway_silent.vbs`"" -WorkingDirectory $ProjectDir
    $Trigger = New-ScheduledTaskTrigger -AtLogOn
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "EvacuMate Permanent Public Online Runtime Gateway" -Force | Out-Null
    Write-Host "[SUCCESS] Registered Windows Scheduled Task: $TaskName" -ForegroundColor Green
} catch {
    Write-Host "[INFO] Scheduled Task registration skipped (User Startup folder shortcut is active and sufficient)." -ForegroundColor Gray
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Auto-reconnect on boot is successfully configured!       " -ForegroundColor Green
Write-Host " The permanent URL will reconnect automatically on boot.   " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
