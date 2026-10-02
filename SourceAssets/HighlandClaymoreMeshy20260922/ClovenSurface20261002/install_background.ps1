param([int]$GateSeconds=60,[string]$Script='install_surface.py')
$ErrorActionPreference='Stop'
$taskDir=$PSScriptRoot
$installScript=if([IO.Path]::IsPathRooted($Script)){$Script}else{Join-Path $taskDir $Script}
$taskDir=Split-Path -Parent $installScript
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
$useBridge=$false
try {
    try { $held=$gate.WaitOne([TimeSpan]::FromSeconds($GateSeconds)) }
    catch [Threading.AbandonedMutexException] { $held=$true; throw 'Previous asset batch ended unexpectedly; preserve state.' }
    if(-not $held){throw 'Asset batch is occupied; no request sent.'}
    $owners=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        $_.CommandLine -match 'D:[\\/]FPS3D[\\/]FPSGAME(?:-mp)?[\\/]' })
    if($owners | Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe'}) {
        throw 'An existing project commandlet is running; preserve state.'
    }
    $running=@($owners | Where-Object {$_.Name -eq 'UnrealEditor.exe'})
    if($running) {
        if($running | Where-Object {$_.CommandLine -match 'FPSGAME-mp[\\/]' -or $_.CommandLine -match '(?i)(?:^|\s)-game(?:\s|$)'}) {
            throw 'A process sharing Content is active; preserve state.'
        }
        $useBridge=$true
    } else {
        $log=Join-Path $taskDir "install-$stamp.log"
        $stdout=Join-Path $taskDir "install-$stamp.stdout.log"
        $oldHeadless=$env:CLOVEN_HEADLESS
        try {
            $env:CLOVEN_HEADLESS='1'
            & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$installScript" -unattended -nop4 -nosplash -nullrhi '-ExecCmds=Interchange.FeatureFlags.Import.FBX 0' "-abslog=$log" *> $stdout
            $result=$LASTEXITCODE
        } finally { $env:CLOVEN_HEADLESS=$oldHeadless }
        Select-String -LiteralPath $log -Pattern 'LogPython:.*(CLOVEN|Error|Traceback)|Error:' | Select-Object -Last 20 | ForEach-Object {$_.Line}
        if($result -ne 0){throw "Cloven installation failed: $result. Log: $log"}
        Write-Output "CLOVEN_COMMANDLET_COMPLETED exit=$result log=$log"
    }
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
if($useBridge) {
    & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript $installScript -QueueWaitSeconds 60 -OutputFile (Join-Path $taskDir "install-$stamp.bridge.txt") -MaxOutputChars 2500
    if($LASTEXITCODE -ne 0){throw "Existing editor import did not complete: $LASTEXITCODE"}
}
