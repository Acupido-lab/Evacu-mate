# EvacuMate - Offline Local Domain Setup
# Registers 'evacumate.local' and 'evacumate' into Windows hosts file for 100% offline access.

$HostsPath = "$env:SystemRoot\System32\drivers\etc\hosts"
$Entry1 = "127.0.0.1    evacumate.local"
$Entry2 = "127.0.0.1    evacumate"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   EvacuMate Offline Permanent Domain Registration        " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

try {
    $content = Get-Content $HostsPath -Raw -ErrorAction Stop
    $updated = $false

    if ($content -notmatch "evacumate\.local") {
        Add-Content -Path $HostsPath -Value "`r`n# EvacuMate Permanent Offline Domain`r`n$Entry1`r`n$Entry2" -ErrorAction Stop
        Write-Host "[SUCCESS] Added 'evacumate.local' and 'evacumate' to Windows hosts file!" -ForegroundColor Green
        $updated = $true
    } else {
        Write-Host "[INFO] 'evacumate.local' is already registered in Windows hosts file." -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "You can now open EvacuMate offline on this PC using:" -ForegroundColor Cyan
    Write-Host " -> http://evacumate.local:8550" -ForegroundColor Yellow
    Write-Host " -> http://evacumate:8550" -ForegroundColor Yellow
} catch {
    Write-Host "[NOTICE] Could not automatically update hosts file (Administrator privileges required)." -ForegroundColor Yellow
    Write-Host "mDNS broadcast is still active for all Wi-Fi and mobile devices!" -ForegroundColor Gray
}

Write-Host ""
