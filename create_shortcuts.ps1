$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath('Desktop')
$ProjectDir = $PSScriptRoot

if (-not $ProjectDir) {
    $ProjectDir = "c:\Users\ryuki a acupido\OneDrive\Desktop\System_GrpProject(IT ELEC),"
}

# 1. EvacuMate App Shortcut
$AppLnk = $WshShell.CreateShortcut("$DesktopPath\EvacuMate App.lnk")
$AppLnk.TargetPath = "$ProjectDir\run.bat"
$AppLnk.WorkingDirectory = $ProjectDir
$AppLnk.Description = "Launch EvacuMate Relief & Shelter Helper (Offline & Local Server)"
$AppLnk.IconLocation = "shell32.dll,14"
$AppLnk.Save()
Write-Host "Created Desktop Shortcut: EvacuMate App.lnk"

# 2. EvacuMate Access Guide Shortcut
$GuideLnk = $WshShell.CreateShortcut("$DesktopPath\EvacuMate Access Guide.lnk")
$GuideLnk.TargetPath = "$ProjectDir\ONLINE_AND_OFFLINE_GUIDE.html"
$GuideLnk.WorkingDirectory = $ProjectDir
$GuideLnk.Description = "EvacuMate Online and Offline Access Guide"
$GuideLnk.IconLocation = "shell32.dll,15"
$GuideLnk.Save()
Write-Host "Created Desktop Shortcut: EvacuMate Access Guide.lnk"

# 3. Create shortcut in user profile Desktop if different from OneDrive Desktop
$UserDesktop = "$env:USERPROFILE\Desktop"
if ((Test-Path $UserDesktop) -and ($UserDesktop -ne $DesktopPath)) {
    $AppLnk2 = $WshShell.CreateShortcut("$UserDesktop\EvacuMate App.lnk")
    $AppLnk2.TargetPath = "$ProjectDir\run.bat"
    $AppLnk2.WorkingDirectory = $ProjectDir
    $AppLnk2.Description = "Launch EvacuMate Relief & Shelter Helper"
    $AppLnk2.IconLocation = "shell32.dll,14"
    $AppLnk2.Save()

    $GuideLnk2 = $WshShell.CreateShortcut("$UserDesktop\EvacuMate Access Guide.lnk")
    $GuideLnk2.TargetPath = "$ProjectDir\ONLINE_AND_OFFLINE_GUIDE.html"
    $GuideLnk2.WorkingDirectory = $ProjectDir
    $GuideLnk2.Description = "EvacuMate Online and Offline Access Guide"
    $GuideLnk2.IconLocation = "shell32.dll,15"
    $GuideLnk2.Save()
    Write-Host "Created Desktop Shortcuts on UserProfile Desktop as well."
}
