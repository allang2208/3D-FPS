param([switch]$SkipBuild)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try { $taskHeld=$taskMutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $taskHeld=$true }
    if (-not $taskHeld) { Write-Output 'Waiting for the UE production batch.' }
    while (-not $taskHeld) {
        try { $taskHeld=$taskMutex.WaitOne(5000) } catch [Threading.AbandonedMutexException] { $taskHeld=$true }
    }
    if (-not $SkipBuild -and (Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe'" | Where-Object { $_.CommandLine -like '*FPSGAME*' })) { throw 'Preserve the open editor; native diagnosis build needs its loaded binaries released.' }
    $stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    if (-not $SkipBuild) {
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -WaitMutex *> (Join-Path $taskRoot "Receipts/build-v6-$stamp.log")
        if ($LASTEXITCODE -ne 0) { throw 'Native diagnosis build failed; see build-v6 log.' }
    }
    $log=Join-Path $taskRoot "Receipts/window-native-v6-$stamp.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' '-run=EcologyWindowDiagnosis' -nullrhi -unattended -nop4 -nosplash "-abslog=$log" *> (Join-Path $taskRoot "Receipts/window-native-stdout-v6-$stamp.log")
    Write-Output "WINDOW_DIAG_EXIT=$LASTEXITCODE LOG=$log"
} finally {
    if ($taskHeld) { $taskMutex.ReleaseMutex() }
    $taskMutex.Dispose()
}
