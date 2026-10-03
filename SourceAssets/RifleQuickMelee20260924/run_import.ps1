param()
$ErrorActionPreference='Stop'
$jobDir='D:/FPS3D/FPSGAME/SourceAssets/RifleQuickMelee20260924'
$project='D:/FPS3D/FPSGAME/FPSGAME.uproject'
$scriptPath=Join-Path $jobDir 'import_animations.py'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
$useBridge=$false
try {
    try { $held=$gate.WaitOne([TimeSpan]::FromSeconds(60)) }
    catch [Threading.AbandonedMutexException] { $held=$true; throw 'Previous UE batch ended unexpectedly; preserve state.' }
    if(-not $held){ Write-Output 'Animation import queued; no assets changed.'; exit 75 }
    $running=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { -not $_.CommandLine -or $_.CommandLine -match 'FPSGAME' })
    # An unrelated scene/material commandlet does not own these ten animation
    # packages. Guard duplicate runs of this exact import; the Python batch
    # additionally checks each target source and unsaved target changes.
    if($running | Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'RifleQuickMelee20260924'}){ throw 'This animation import is already running; preserve state.' }
    if($running | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(^|\s)-game(\s|$)'}){ $useBridge=$true }
    else {
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' $project -run=pythonscript "-script=$scriptPath" -unattended -nop4 -nosplash -nullrhi -multiprocess "-abslog=$jobDir/import_commandlet.log" *> "$jobDir/import_commandlet.stdout.log"
        $result=$LASTEXITCODE
        Select-String -LiteralPath "$jobDir/import_commandlet.log" -Pattern 'LogPython:.*(MELEE_|Error|Traceback)' | Select-Object -Last 14 | ForEach-Object {$_.Line}
        if($result -ne 0){throw "Animation commandlet failed: $result"}
    }
} finally { if($held){$gate.ReleaseMutex()};$gate.Dispose() }
if($useBridge){
    $stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript $scriptPath -QueueWaitSeconds 60 -OutputFile "$jobDir/import.$stamp.bridge.txt" -MaxOutputChars 3000
    if($LASTEXITCODE -ne 0){throw "Existing editor import failed: $LASTEXITCODE"}
}
