param([int]$QueueWaitSeconds = 600)
$ErrorActionPreference = 'Stop'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) }
    catch [Threading.AbandonedMutexException] {
        $held = $true
        throw 'Prior UE operation has unknown completion; preserve state.'
    }
    if (-not $held) { throw 'UE batch gate is busy; no import was launched.' }
    $busy = @(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -match '^UnrealEditor' -and $_.CommandLine -match 'FPSGAME') -or
        (($_.Name -eq 'UnrealBuildTool.exe' -or $_.Name -eq 'dotnet.exe') -and $_.CommandLine -match 'UnrealBuildTool' -and $_.CommandLine -match 'FPSGAMEEditor')
    })
    if ($busy.Count -gt 0) { throw 'FPSGAME editor/build is active; use the existing bridge or wait, without starting a competing process.' }
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    $scriptPath = Join-Path $PSScriptRoot 'import_assets.py'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$scriptPath" -unattended -nop4 -nosplash -NullRHI -nosound "-abslog=$PSScriptRoot/import.log" *> "$PSScriptRoot/import-console.log"
    $code=$LASTEXITCODE
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
exit $code
