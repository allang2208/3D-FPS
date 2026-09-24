# Wait for the FPSGAME editor to close, then: re-author NS_FurnaceBlackSmoke v2 (headless)
# and run the regular editor build. One serialized window, no forced kills, bounded waiting.
$ErrorActionPreference = 'Continue'
$editorProc = 'UnrealEditor'
$log = 'D:\FPS3D\FPSGAME\Saved\furnace_v2_sequence.log'
function Say($m) { $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m; Add-Content -Path $log -Value $line; Write-Output $line }
Say 'SEQUENCE-START waiting for editor close (max 60 min)'
$deadline = (Get-Date).AddMinutes(60)
$freeStreak=0
while ((Get-Date) -lt $deadline) {
    if (Get-Process $editorProc -ErrorAction SilentlyContinue) { $freeStreak=0 } else { $freeStreak++ }
    if ($freeStreak -ge 2) { break }        # 连续两次 1s 采样无编辑器才动手，避开重启瞬间
    Start-Sleep -Seconds 1
}
if (Get-Process $editorProc -ErrorAction SilentlyContinue) { Say 'TIMEOUT editor still open; nothing was built or saved'; exit 2 }
Say 'EDITOR-CLOSED detected; starting author commandlet'
& 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' `
    -run=pythonscript -script='D:\FPS3D\FPSGAME\Tools\Fluids\author_furnace_black_smoke.py' `
    -unattended -nop4 -nosplash -NullRHI -abslog='D:\FPS3D\FPSGAME\Saved\furnace_author_v2seq.log' | Out-Null
$authorExit = $LASTEXITCODE
$savedOk = Select-String -Path 'D:\FPS3D\FPSGAME\Saved\furnace_author_v2seq.log' -Pattern 'FURNACE_SMOKE_SAVED' -Quiet
Say ('AUTHOR exit={0} saved={1}' -f $authorExit, $savedOk)
if (-not $savedOk) { Say 'AUTHOR-FAILED stopping before build (asset left as-is on disk)'; exit 3 }
Say 'BUILD-START'
try {
    & 'D:\FPS3D\FPSGAME\Tools\Build\Build-Editor.ps1' *> 'D:\FPS3D\FPSGAME\Saved\furnace_v2seq_build.log'
    $buildExit = $LASTEXITCODE
} catch {
    # Build-Editor.ps1 的 throw（编辑器占用）是语句终止错误，会穿透 & 直接杀死本脚本——必须接住走重试。
    Say ('BUILD-REFUSED: ' + $_.Exception.Message)
    $buildExit = 1
}
Say ('BUILD exit={0}' -f $buildExit)
if ($buildExit -ne 0) {
    # One retry window: maybe the editor reopened mid-flight; wait briefly for another close.
    $retryBy = (Get-Date).AddMinutes(10)
    while ((Get-Date) -lt $retryBy -and (Get-Process $editorProc -ErrorAction SilentlyContinue)) { Start-Sleep -Seconds 10 }
    if (-not (Get-Process $editorProc -ErrorAction SilentlyContinue)) {
        Say 'BUILD-RETRY after editor closed again'
        & 'D:\FPS3D\FPSGAME\Tools\Build\Build-Editor.ps1' *> 'D:\FPS3D\FPSGAME\Saved\furnace_v2seq_build2.log'
        $buildExit = $LASTEXITCODE
        Say ('BUILD-RETRY exit={0}' -f $buildExit)
    }
}
Say $(if ($buildExit -eq 0) { 'SEQUENCE-DONE asset v2 saved + editor rebuilt' } else { 'SEQUENCE-PARTIAL asset v2 saved; build needs another editor-free window' })
