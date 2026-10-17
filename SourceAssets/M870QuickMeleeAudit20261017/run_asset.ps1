param([string]$ScriptName = 'read_inputs.py')
$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$scriptFile = Join-Path $PSScriptRoot $ScriptName
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$gate = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    for($attempt=0;$attempt -lt 180 -and -not $held;$attempt++) {
        try {$held=$gate.WaitOne(10000)} catch [Threading.AbandonedMutexException] {$held=$true}
        if(-not $held -and ($attempt % 6 -eq 0)){Write-Output 'Waiting for the existing UE asset batch.'}
    }
    if(-not $held){throw 'UE asset batch remains occupied; no read or write started.'}
    $deadline=[DateTime]::UtcNow.AddMinutes(20);$nextProgress=[DateTime]::UtcNow
    while(-not @(Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue).Count -and
        @(Get-Process -Name UnrealEditor-Cmd,dotnet,UnrealBuildTool,cl,link -ErrorAction SilentlyContinue).Count) {
        if([DateTime]::UtcNow -gt $deadline){throw 'Existing backend process remains active; no duplicate commandlet started.'}
        if([DateTime]::UtcNow -ge $nextProgress){Write-Output 'Waiting for the existing backend process.';$nextProgress=[DateTime]::UtcNow.AddSeconds(60)}
        Start-Sleep -Seconds 5
    }
    if(@(Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue).Count) {
        $gate.ReleaseMutex();$held=$false
        & "$projectRoot/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $scriptFile -QueueWaitSeconds 600 -RequestTimeoutSeconds 300 -OutputFile (Join-Path $PSScriptRoot "$ScriptName-bridge-$stamp.txt") -MaxOutputChars 2200
        if($LASTEXITCODE -ne 0){throw 'Existing editor asset batch failed; read the saved bridge output.'}
    } else {
        $log=Join-Path $PSScriptRoot "$ScriptName-commandlet-$stamp.log"
        $console=Join-Path $PSScriptRoot "$ScriptName-console-$stamp.log"
        Write-Output "Running background animation authoring step: $ScriptName"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$scriptFile" -unattended -nop4 -nosplash -nosound -nullrhi "-abslog=$log" *> $console
        if($LASTEXITCODE -ne 0){throw "Animation authoring commandlet failed; see $log"}
        Write-Output "Completed background animation authoring step: $ScriptName"
    }
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
