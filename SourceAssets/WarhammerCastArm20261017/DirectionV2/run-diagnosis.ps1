$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while(-not $taskHeld) {
        try {$taskHeld=$taskGate.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
        if(-not $taskHeld){Write-Output 'Waiting for the existing UE asset batch.'}
    }
    while($taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool.*FPSGAMEEditor')
    })) {foreach($taskProcess in $taskBusy){Wait-Process -Id $taskProcess.ProcessId -ErrorAction SilentlyContinue}}
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'An editor is open; keep it intact and use the existing bridge for the read-only diagnosis.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript '-script=D:/FPS3D/FPSGAME/Tools/PlayerBody/run_hammer_cast_diagnosis20261017.py' -unattended -nosplash -nullrhi -nosound -NoLiveCoding "-UserDir=$PSScriptRoot/CommandletUser/" "-abslog=$PSScriptRoot/native-graph.log" *> "$PSScriptRoot/native-graph-stdout.log"
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;finished=(Get-Date).ToString('s');kind='offline native pose diagnosis; no gameplay or rendering'} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/native-graph-receipt.json" -Encoding utf8
    Write-Output "Native graph diagnosis exit=$taskExit"
    exit $taskExit
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
