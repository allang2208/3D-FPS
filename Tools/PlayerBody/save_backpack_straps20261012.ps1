$ErrorActionPreference='Stop'
$packProject='D:/FPS3D/FPSGAME'
$packRoot="$packProject/SourceAssets/BackpackStraps20261012"
$packGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$packHeld=$false
try {
    try { $packHeld=$packGate.WaitOne([TimeSpan]::FromSeconds(300)) } catch [Threading.AbandonedMutexException] { $packHeld=$true }
    if (-not $packHeld) { throw 'The UE asset queue is still occupied.' }
    $packDeadline=[DateTime]::UtcNow.AddMinutes(15)
    $packWaiting=$false
    while (Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
        ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME')
    }) {
        if (-not $packWaiting) { Write-Output 'Waiting for the active build or asset commandlet.'; $packWaiting=$true }
        if ([DateTime]::UtcNow -gt $packDeadline) { throw 'The build or asset commandlet remains active.' }
        Start-Sleep -Seconds 10
    }
    if (Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME.uproject' }) {
        throw 'Use the active editor asset bridge to save this loaded backpack.'
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$packProject/FPSGAME.uproject" -run=pythonscript "-script=$packProject/Tools/PlayerBody/save_backpack_straps20261012.py" -NullRHI -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$packRoot/save-backpack.log" *> "$packRoot/save-backpack-console.txt"
    if ($LASTEXITCODE -ne 0) { throw "Backpack save failed; see $packRoot/save-backpack.log." }
    Write-Output 'BACKPACK_STRAPS_BACKGROUND_SAVED'
} finally {
    if ($packHeld) { $packGate.ReleaseMutex() }
    $packGate.Dispose()
}
