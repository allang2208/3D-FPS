param([string]$Script='save_assets.py',[string]$ReceiptName=('sportsCap-'+(Get-Date -Format 'yyyyMMdd-HHmmss')),[switch]$EndPlayAuthorized)
$ErrorActionPreference='Stop'
$sportsCapProject='D:/FPS3D/FPSGAME'
$sportsCapLogs=Join-Path $sportsCapProject 'SourceAssets/SportsCap20261024/Logs'
[void](New-Item -ItemType Directory -Force -Path $sportsCapLogs)
$sportsCapScript=Join-Path $sportsCapProject ('Tools/SportsCap/'+$Script)
$sportsCapOutput=Join-Path $sportsCapLogs ($ReceiptName+'.txt')
if(Test-Path -LiteralPath $sportsCapOutput){throw 'Use a fresh sportsCap receipt name.'}
function Test-SportsCapProjectOwner($sportsCapProcess){
    foreach($sportsCapMatch in [regex]::Matches($sportsCapProcess.CommandLine,'"([^"]+\.uproject)"|(\S+\.uproject)')){
        $sportsCapPath=if($sportsCapMatch.Groups[1].Success){$sportsCapMatch.Groups[1].Value}else{$sportsCapMatch.Groups[2].Value}
        if($sportsCapPath.Replace('\','/') -eq "$sportsCapProject/FPSGAME.uproject"){return $true}
    }
    $sportsCapModule=@((Get-Process -Id $sportsCapProcess.ProcessId -ErrorAction SilentlyContinue).Modules | Where-Object {$_.ModuleName -eq 'UnrealEditor-FPSGAME.dll'})
    return [bool]@($sportsCapModule | Where-Object {$_.FileName.Replace('\','/') -eq "$sportsCapProject/Binaries/Win64/UnrealEditor-FPSGAME.dll"}).Count
}
$sportsCapProcesses=@(Get-CimInstance Win32_Process)
$sportsCapEditor=@($sportsCapProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)' -and (Test-SportsCapProjectOwner $_)})
if($sportsCapEditor.Count){
    $sportsWindow=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$sportsWindowHeld=$false
    try {
        # The nested bridge calls re-enter this same thread's mutex. End-play and
        # saving stay in one editor batch; no unrelated work runs under the gate.
        try{$sportsWindowHeld=$sportsWindow.WaitOne([TimeSpan]::FromSeconds(3600))}catch [Threading.AbandonedMutexException]{$sportsWindowHeld=$true}
        if(-not $sportsWindowHeld){throw 'Editor batch unavailable; no request sent.'}
        if($EndPlayAuthorized){
            & (Join-Path $sportsCapProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript (Join-Path $sportsCapProject 'Tools/WorkwearSet/end_play.py') -OutputFile (Join-Path $sportsCapLogs ($ReceiptName+'-end-play.txt')) -MaxOutputChars 700 -QueueWaitSeconds 60 -RequestTimeoutSeconds 120
            if($LASTEXITCODE -ne 0){throw 'End-play request failed; retain editor state.'}
        }
        & (Join-Path $sportsCapProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $sportsCapScript -OutputFile $sportsCapOutput -MaxOutputChars 2500 -QueueWaitSeconds 60 -RequestTimeoutSeconds 1800
        $sportsWindowExit=$LASTEXITCODE
    }finally{if($sportsWindowHeld){$sportsWindow.ReleaseMutex()};$sportsWindow.Dispose()}
    exit $sportsWindowExit
}
$sportsCapGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$sportsCapHeld=$false
try{
    Write-Output 'Queued for shared asset batch.'
    try{$sportsCapHeld=$sportsCapGate.WaitOne()}catch [Threading.AbandonedMutexException]{$sportsCapHeld=$true}
    while($true){
        $sportsCapBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and (Test-SportsCapProjectOwner $_))
        })
        if(-not $sportsCapBusy.Count){break}
        if(@($sportsCapBusy | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)'}).Count){throw 'The project editor appeared; retain it and use the bridge on the next batch.'}
        Write-Output 'Waiting for the project engine/build owner.'
        try{Wait-Process -Id $sportsCapBusy[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $sportsCapBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    $sportsCapLog=Join-Path $sportsCapLogs ($ReceiptName+'.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$sportsCapProject/FPSGAME.uproject" '-run=pythonscript' "-script=$sportsCapScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$sportsCapLog" *> $sportsCapOutput
    $sportsCapExit=$LASTEXITCODE;Write-Output "SportsCap commandlet exit=$sportsCapExit; log=$sportsCapLog";Get-Content -LiteralPath $sportsCapOutput -Tail 3;exit $sportsCapExit
}finally{if($sportsCapHeld){$sportsCapGate.ReleaseMutex()};$sportsCapGate.Dispose()}
