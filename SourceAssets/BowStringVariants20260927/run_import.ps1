param([string]$Script='import_assets.py')
$ErrorActionPreference='Stop'
$jobDir=$PSScriptRoot
$scriptPath=Join-Path $jobDir $Script
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
$bridge=$false
try {
    try { $held=$gate.WaitOne([TimeSpan]::FromSeconds(50)) }
    catch [Threading.AbandonedMutexException] { $held=$true; throw 'Previous UE batch ended unexpectedly; preserve state.' }
    if(-not $held){throw 'UE batch gate occupied; no assets changed.'}
    $running=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {-not $_.CommandLine -or $_.CommandLine -match 'FPSGAME'})
    if($running | Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe'}){throw 'An existing project commandlet is running; preserve state.'}
    if($running | Where-Object {$_.Name -eq 'UnrealEditor.exe'}) {$bridge=$true}
    else {
        $log=Join-Path $jobDir "install.$stamp.log"
        $out=Join-Path $jobDir "install.$stamp.stdout.log"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$scriptPath" -unattended -nop4 -nosplash -nullrhi "-abslog=$log" *> $out
        $result=$LASTEXITCODE
        Select-String -LiteralPath $log -Pattern 'LogPython:.*(BOW_STRING_|Error|Traceback)|Error:' | Select-Object -Last 12 | ForEach-Object {$_.Line}
        if($result -ne 0){throw "Bow string asset save failed: $result. Log: $log"}
        Write-Output "BOW_STRING_COMMANDLET_COMPLETED exit=$result log=$log"
    }
} finally { if($held){$gate.ReleaseMutex()}; $gate.Dispose() }
if($bridge) {
    & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript $scriptPath -QueueWaitSeconds 300 -OutputFile "$jobDir/install.$stamp.bridge.json" -MaxOutputChars 2400
    if($LASTEXITCODE -ne 0){throw "Existing editor bridge did not complete: $LASTEXITCODE"}
}