param([string]$ScriptName='read_runtime.py')
$ErrorActionPreference='Stop'
$jobDir='D:/FPS3D/FPSGAME/SourceAssets/SVDChargeGrasp20260924'
$scriptPath=Join-Path $jobDir $ScriptName
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(60))}
    catch [Threading.AbandonedMutexException] {$held=$true;throw 'Previous UE batch ended unexpectedly.'}
    if(-not $held){Write-Output 'UE batch busy; this script was not run.';exit 75}
    $running=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME'})
    if($running | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(^|\s)-game(\s|$)'}){throw 'Use existing editor through the shared bridge.'}
    if($running | Where-Object {$_.CommandLine -match 'SVDChargeGrasp20260924'}){throw 'This SVD batch is already running.'}
    $stem=[IO.Path]::GetFileNameWithoutExtension($ScriptName)
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$scriptPath" -unattended -nop4 -nosplash -nullrhi -multiprocess "-abslog=$jobDir/$stem.commandlet.log" *> "$jobDir/$stem.stdout.log"
    $result=$LASTEXITCODE
    Select-String -LiteralPath "$jobDir/$stem.commandlet.log" -Pattern 'LogPython:.*(SVD_GRASP_|Error|Traceback)' | Select-Object -Last 10 | ForEach-Object {$_.Line}
    if($result -ne 0){throw "SVD commandlet failed: $result"}
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
