$ErrorActionPreference='Stop'
$sleeveProject='D:/FPS3D/FPSGAME'
$sleeveOutput="$sleeveProject/SourceAssets/SleeveSpikeRepair20261006"
$sleeveGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$sleeveHeld=$false
try {
    try { $sleeveHeld=$sleeveGate.WaitOne([TimeSpan]::FromSeconds(300)) } catch [Threading.AbandonedMutexException] { $sleeveHeld=$true }
    if (-not $sleeveHeld) { throw 'Existing UE batch remains active.' }
    $sleeveDeadline=[DateTime]::UtcNow.AddMinutes(20)
    while(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME') }) {
        if([DateTime]::UtcNow -gt $sleeveDeadline){throw 'Existing build or commandlet remains active.'}
        Start-Sleep -Seconds 10
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$sleeveProject/FPSGAME.uproject" -run=pythonscript "-script=$sleeveProject/Tools/FirstPersonLegs/save_continuous_owner_shoulders.py" -NullRHI -unattended -nop4 -nosplash -nosound -Multiprocess "-abslog=$sleeveOutput/save-shoulders.log" *> "$sleeveOutput/save-shoulders-console.txt"
    if($LASTEXITCODE -ne 0){throw 'Owner shoulder asset save failed; see save-shoulders.log.'}
    Write-Output 'CONTINUOUS_OWNER_SHOULDERS_SAVED'
} finally { if($sleeveHeld){$sleeveGate.ReleaseMutex()}; $sleeveGate.Dispose() }