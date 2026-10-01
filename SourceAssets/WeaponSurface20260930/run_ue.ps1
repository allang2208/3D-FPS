param([Parameter(Mandatory=$true)][string]$Script,[int]$GateSeconds=120,[switch]$WithRHI,[switch]$FileCache)
# Runs one UE Python script: through the project bridge when an FPSGAME editor is
# open, otherwise as a headless commandlet. Holds the shared UE batch gate.
$ErrorActionPreference='Stop'
$jobDir=$PSScriptRoot
$scriptPath=if([IO.Path]::IsPathRooted($Script)){$Script}else{Join-Path $jobDir $Script}
$name=[IO.Path]::GetFileNameWithoutExtension($scriptPath)
$logDir=Join-Path $jobDir 'logs'
[IO.Directory]::CreateDirectory($logDir)|Out-Null
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false;$bridge=$false
try {
    try { $held=$gate.WaitOne([TimeSpan]::FromSeconds($GateSeconds)) }
    catch [Threading.AbandonedMutexException] { $held=$true; throw 'Previous UE batch ended unexpectedly; preserve state.' }
    if(-not $held){throw 'UE batch gate occupied; no assets changed.'}
    # Only this project counts: D:/FPS3D/FPSGAME-mp editors also contain "FPSGAME" in their name.
    $project='D:[\\/]FPS3D[\\/]FPSGAME[\\/]FPSGAME\.uproject'
    $all=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'")
    # UnrealEditor.exe -game is a standalone game and has no editor Python node.
    $running=@($all | Where-Object {$_.CommandLine -match $project -and $_.CommandLine -notmatch '(?i)(?:^|\s)-game(?:\s|$)'})
    $others=@($all | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch $project})
    if($running | Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe'}){throw 'An existing project commandlet is running; preserve state.'}
    if($running | Where-Object {$_.Name -eq 'UnrealEditor.exe'}) {
        # FPSGAME-mp editors report the same project name; pin the node by project_root.
        $node=(& py -3.11 (Join-Path $jobDir 'find_node.py')) | Select-Object -Last 1
        if($LASTEXITCODE -ne 0 -or -not $node){throw 'No remote-execution node for D:/FPS3D/FPSGAME answered. No assets changed.'}
        $bridge=$true
    }
    else {
        $log=Join-Path $logDir "$name.$stamp.log"
        $out=Join-Path $logDir "$name.$stamp.stdout.log"
        # Skeletal FBX export needs render resources; everything else runs render-less.
        $rhi=@(if(-not $WithRHI){'-nullrhi'})
        if($FileCache){$rhi+='-DDC=(ProjectPak,EnginePak,Local)'}
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$scriptPath" -unattended -nop4 -nosplash @rhi "-abslog=$log" *> $out
        $result=$LASTEXITCODE
        Select-String -LiteralPath $log -Pattern 'LogPython:.*(WEAPON_SURFACE|A762_SURFACE|Error|Traceback)|Error:' | Select-Object -Last 20 | ForEach-Object {$_.Line}
        if($result -ne 0){throw "UE script failed: $result. Log: $log"}
        Write-Output "UE_COMMANDLET_COMPLETED exit=$result log=$log"
    }
} finally { if($held){$gate.ReleaseMutex()}; $gate.Dispose() }
if($bridge) {
    & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript $scriptPath -PythonNodeId $node -QueueWaitSeconds 300 -OutputFile (Join-Path $logDir "$name.$stamp.bridge.txt") -MaxOutputChars 2400
    if($LASTEXITCODE -ne 0){throw "Existing editor bridge did not complete: $LASTEXITCODE"}
}
