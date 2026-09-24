# Build-only waiter for the furnace smoke v4 delivery (asset already saved 23:22).
# Waits for ANY FPSGAME UnrealEditor.exe / UnrealEditor-Cmd.exe to clear (same detection as
# Build-Editor.ps1, so it also yields to other sessions' commandlets), then runs the regular
# editor build once with a single retry window. Never kills or messages other processes.
$ErrorActionPreference = 'Continue'
$log = 'D:\FPS3D\FPSGAME\Saved\furnace_build_only.log'
function Say($m) { $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m; Add-Content -Path $log -Value $line; Write-Output $line }
function Busy {
    @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match [regex]::Escape('FPSGAME.uproject')
    }).Count
}
Say 'BUILD-ONLY-START waiting for all FPSGAME editor/cmd processes to clear (max 45 min)'
$deadline = (Get-Date).AddMinutes(45)
$free = 0
while ((Get-Date) -lt $deadline) {
    if ((Busy) -eq 0) { $free++ } else { $free = 0 }
    if ($free -ge 3) { break }                       # 连续 3 次 1s 采样全空才动手（避开重启/新 commandlet 瞬间）
    Start-Sleep -Seconds 1
}
if ((Busy) -gt 0) { Say 'TIMEOUT busy; nothing was built'; exit 2 }
Say 'CLEAR detected; starting build'
try {
    & 'D:\FPS3D\FPSGAME\Tools\Build\Build-Editor.ps1' *> 'D:\FPS3D\FPSGAME\Saved\furnace_v4_build.log'
    $buildExit = $LASTEXITCODE
} catch {
    Say ('BUILD-REFUSED: ' + $_.Exception.Message)   # throw 是语句终止错误，会穿透 & 杀死本脚本——必须接住
    $buildExit = 1
}
Say ('BUILD exit={0}' -f $buildExit)
if ($buildExit -ne 0) {
    $retryBy = (Get-Date).AddMinutes(12)
    while ((Get-Date) -lt $retryBy -and (Busy) -gt 0) { Start-Sleep -Seconds 5 }
    if ((Busy) -eq 0) {
        Say 'BUILD-RETRY after window cleared again'
        try {
            & 'D:\FPS3D\FPSGAME\Tools\Build\Build-Editor.ps1' *> 'D:\FPS3D\FPSGAME\Saved\furnace_v4_build2.log'
            $buildExit = $LASTEXITCODE
        } catch { Say ('BUILD-RETRY-REFUSED: ' + $_.Exception.Message); $buildExit = 1 }
        Say ('BUILD-RETRY exit={0}' -f $buildExit)
    }
}
Say $(if ($buildExit -eq 0) { 'BUILD-ONLY-DONE editor rebuilt (v3 rain + v4 softening + workbench)' } else { 'BUILD-ONLY-PARTIAL build needs another clear window' })
