$ErrorActionPreference='Stop'
$m24Root='D:/FPS3D/FPSGAME'
$m24Out=Join-Path $m24Root 'SourceAssets/M24PhysicalScope20261030'
$m24Gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$m24Held=$false
try {
    Write-Output 'Waiting for the existing UE asset batch gate.'
    try {$m24Held=$m24Gate.WaitOne([TimeSpan]::FromMinutes(15))}
    catch [Threading.AbandonedMutexException] {$m24Held=$true}
    if(-not $m24Held){throw 'UE asset gate remains busy; no process stopped.'}
    $m24Processes=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'
    })
    if($m24Processes | Where-Object Name -eq 'UnrealEditor-Cmd.exe'){throw 'Existing commandlet retained; asset import deferred.'}
    $m24Stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    if($m24Processes | Where-Object Name -eq 'UnrealEditor.exe') {
        & "$m24Root/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript "$m24Out/install.py" -QueueWaitSeconds 60 -RequestTimeoutSeconds 180 -OutputFile "$m24Out/install-$m24Stamp.json" -MaxOutputChars 1800
    } else {
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$m24Root/FPSGAME.uproject" -run=pythonscript "-script=$m24Out/install.py" -unattended -nop4 -nosplash -nosound -nullrhi "-abslog=$m24Out/install-$m24Stamp.log" *> "$m24Out/install-$m24Stamp.stdout.txt"
    }
    if($LASTEXITCODE -ne 0){throw 'M24 material authoring failed; see batch log.'}
    Write-Output 'M24 physical lens assets saved; editor/game not launched.'
} finally {if($m24Held){$m24Gate.ReleaseMutex()};$m24Gate.Dispose()}
