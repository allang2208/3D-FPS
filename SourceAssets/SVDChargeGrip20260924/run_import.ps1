param()
$ErrorActionPreference='Stop'
$jobDir='D:/FPS3D/FPSGAME/SourceAssets/SVDChargeGrip20260924'
$scriptPath=Join-Path $jobDir 'import_animations.py'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try { $held=$gate.WaitOne([TimeSpan]::FromSeconds(60)) }
    catch [Threading.AbandonedMutexException] { $held=$true; throw 'Previous UE batch ended unexpectedly; preserve state.' }
    if(-not $held){ Write-Output 'Animation import queued; no assets changed.'; exit 75 }
    $running=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { -not $_.CommandLine -or $_.CommandLine -match 'FPSGAME' })
    if($running | Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'SVDChargeGrip20260924'}){ throw 'This animation import is already running; preserve state.' }
    if($running | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(^|\s)-game(\s|$)'}){
        throw 'An interactive editor is open; use its identified Python node through the shared bridge.'
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$scriptPath" -unattended -nop4 -nosplash -nullrhi -multiprocess "-abslog=$jobDir/import_commandlet.log" *> "$jobDir/import_commandlet.stdout.log"
    $result=$LASTEXITCODE
    Select-String -LiteralPath "$jobDir/import_commandlet.log" -Pattern 'LogPython:.*(SVD_CHARGE_|Error|Traceback)' | Select-Object -Last 10 | ForEach-Object {$_.Line}
    if($result -ne 0){throw "Animation commandlet failed: $result"}
} finally { if($held){$gate.ReleaseMutex()};$gate.Dispose() }
