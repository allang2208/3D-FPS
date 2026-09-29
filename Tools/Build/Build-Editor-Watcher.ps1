# Watcher: build the FPSGAMEEditor target once no UnrealEditor/UnrealEditor-Cmd process is
# running (parallel-session headless commandlets also trip the Build-Editor guard), retrying
# when a transient instance reappears. Status -> Saved/BuildEditor/watcher-editorbuild-hpmult-20260928.status.
$ErrorActionPreference = 'Continue'
$status = 'D:/FPS3D/FPSGAME/Saved/BuildEditor/watcher-editorbuild-hpmult-20260928.status'
function Say($m) { Add-Content -Path $status -Value ("{0} {1}" -f (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'), $m) -Encoding utf8 }
function UEBusy { [bool](Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) }
Set-Content -Path $status -Value ("{0} watcher armed (v2 retry)" -f (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')) -Encoding utf8

for ($attempt = 1; $attempt -le 5; $attempt++) {
    $deadline = (Get-Date).AddMinutes(90)
    while ((Get-Date) -lt $deadline -and (UEBusy)) { Start-Sleep -Seconds 20 }
    if (UEBusy) { Say ("attempt {0}: still busy after 90min" -f $attempt); continue }
    Start-Sleep -Seconds 10
    if (UEBusy) { Say ("attempt {0}: transient instance reappeared" -f $attempt); continue }
    $out = & powershell -NoProfile -ExecutionPolicy Bypass -File 'D:/FPS3D/FPSGAME/Tools/Build/Build-Editor.ps1' 2>&1
    $code = $LASTEXITCODE
    Say ("attempt {0}: Build-Editor.ps1 exit={1}" -f $attempt, $code)
    Say ($out | Select-Object -Last 2 | Out-String).Trim()
    if ($code -eq 0) { Say 'SUCCESS'; exit 0 }
    Start-Sleep -Seconds 45
}
Say 'FAILED after 5 attempts'
exit 5
