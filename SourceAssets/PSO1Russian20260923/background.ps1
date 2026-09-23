param([string]$Script='import_assets.py')
$ErrorActionPreference='Stop'
$caseDir='D:/FPS3D/FPSGAME/SourceAssets/PSO1Russian20260923'
$job=[IO.Path]::GetFileNameWithoutExtension($Script)
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(900))}
    catch [Threading.AbandonedMutexException] {$held=$true; throw 'Previous UE batch ended unexpectedly; preserve state.'}
    if(-not $held){throw 'UE batch gate unavailable; no operation started.'}
    $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        -not $_.CommandLine -or $_.CommandLine -match 'FPSGAME'
    })
    if($editors.Count){throw 'FPSGAME is running. Preserve that process; use the existing bridge if available.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$caseDir/$Script" -unattended -nop4 -nosplash -nullrhi "-abslog=$caseDir/$job.log" *> "$caseDir/$job.stdout.log"
    $result=$LASTEXITCODE
    Select-String -LiteralPath "$caseDir/$job.log" -Pattern 'LogPython:.*(PSO1|Error|Traceback)' | Select-Object -Last 12 | ForEach-Object {$_.Line}
    exit $result
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
