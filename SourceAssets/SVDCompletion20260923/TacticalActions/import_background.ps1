$ErrorActionPreference='Stop'
$caseDir='D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923/TacticalActions'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(900))}
    catch [Threading.AbandonedMutexException] {$held=$true; throw 'Previous UE batch ended unexpectedly; preserve state.'}
    if(-not $held){throw 'UE batch gate unavailable; no import started.'}
    $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        -not $_.CommandLine -or $_.CommandLine -match 'FPSGAME'
    })
    if($editors.Count){throw 'FPSGAME is running. Use the existing project bridge instead.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$caseDir/import_actions.py" -unattended -nop4 -nosplash -nullrhi "-abslog=$caseDir/import.log" *> "$caseDir/import_stdout.log"
    $result=$LASTEXITCODE
    Select-String -LiteralPath "$caseDir/import.log" -Pattern 'SVD_TACTICAL_|Traceback|Error:' | Select-Object -Last 15 | ForEach-Object {$_.Line}
    exit $result
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
