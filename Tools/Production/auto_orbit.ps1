$ErrorActionPreference = 'Continue'
$dir = 'D:\FPS3D\FPSGAME\Saved\ProductionTreeHealth'
$status = "$dir\auto_orbit_status.txt"
$log = "$dir\auto_orbit.log"
"running" | Set-Content $status
function L($m) { $m | Add-Content $log }

L "[auto] start $(Get-Date -Format 'HH:mm:ss')"

# 清理旧产物
Remove-Item "$dir\orbit_DONE.txt","$dir\orbit_log.txt" -ErrorAction SilentlyContinue
Remove-Item "$dir\orbit_*.png" -ErrorAction SilentlyContinue

# 1) 拉编辑器（带地图）
$elog = "$dir\editor-stub-20260929.log"
if (Test-Path $elog) { Remove-Item $elog -Force }
$args_ = '"D:/FPS3D/FPSGAME/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -nosplash -NoSound -NoLiveCoding -abslog="' + $elog + '"'
$proc = Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $args_ -WindowStyle Hidden -PassThru
L "[auto] editor PID=$($proc.Id)"

$bridge = 'D:\FPS3D\FPSGAME\Tools\AssetPipeline\mcp_call_codex.ps1'
$probe = 'D:\FPS3D\FPSGAME\Tools\Production\probe_asset_ready.py'
$orbit = 'D:\FPS3D\FPSGAME\Tools\Production\orbit_find_stub.py'

# 2) 等端口+资产（最多 6 分钟）
$ready = $false
for ($i = 0; $i -lt 24; $i++) {
    Start-Sleep -Seconds 15
    if ($proc.HasExited) { L "[auto] editor died at poll $i"; break }
    Remove-Item "$dir\probe_auto.json" -ErrorAction SilentlyContinue
    $null = & powershell -NoProfile -ExecutionPolicy Bypass -File $bridge -QueueWaitSeconds 20 -PythonScript $probe -OutputFile "$dir\probe_auto.json" 2>&1
    if ((Test-Path "$dir\probe_auto.json") -and ((Get-Content "$dir\probe_auto.json" -Raw) -match 'LOAD=M_CutUpperMotion')) {
        $ready = $true
        L "[auto] ready after $(($i+1)*15)s"
        break
    }
}
if (-not $ready) {
    "editor_not_ready" | Set-Content $status
    if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    L "[auto] give up (not ready)"
    exit 1
}

# 3) 立刻环拍
Remove-Item "$dir\orbit_auto.json" -ErrorAction SilentlyContinue
$null = & powershell -NoProfile -ExecutionPolicy Bypass -File $bridge -QueueWaitSeconds 60 -PythonScript $orbit -OutputFile "$dir\orbit_auto.json" 2>&1

# 4) 等完成（最多 3 分钟）
$done = $false
for ($j = 0; $j -lt 12; $j++) {
    Start-Sleep -Seconds 15
    if (Test-Path "$dir\orbit_DONE.txt") { $done = $true; break }
    if ($proc.HasExited) { L "[auto] editor died during orbit at poll $j"; break }
}
if ($done) {
    "orbit_done" | Set-Content $status
    L "[auto] ORBIT DONE $(Get-Date -Format 'HH:mm:ss')"
} else {
    "orbit_incomplete" | Set-Content $status
    L "[auto] orbit incomplete"
}
# 5) 收尾杀编辑器
if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force; L "[auto] editor killed" }
L "[auto] end"
