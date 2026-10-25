param([string]$Script='save_assets.py',[string]$ReceiptName=('beltAsset-'+(Get-Date -Format 'yyyyMMdd-HHmmss')),[switch]$EndPlayAuthorized)
$ErrorActionPreference='Stop'
$beltAssetProject='D:/FPS3D/FPSGAME'
$beltAssetLogs=Join-Path $beltAssetProject 'SourceAssets/CombatBeltsIntegration20261025/Logs'
[void](New-Item -ItemType Directory -Force -Path $beltAssetLogs)
$beltAssetScript=Join-Path $beltAssetProject ('Tools/CombatBeltsIntegration/'+$Script)
$beltAssetOutput=Join-Path $beltAssetLogs ($ReceiptName+'.txt')
if(Test-Path -LiteralPath $beltAssetOutput){throw 'Use a fresh beltAsset receipt name.'}
function Save-CombatBeltsExecution([int]$Code){
    @{exit_code=$Code;script=$Script;script_sha256=(Get-FileHash -LiteralPath $beltAssetScript -Algorithm SHA256).Hash.ToLowerInvariant();output=$beltAssetOutput;finished_at=(Get-Date -Format o)} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $beltAssetProject 'SourceAssets/CombatBeltsIntegration20261025/asset-execution.json') -Encoding utf8
}
function Test-CombatBeltsIntegrationProjectOwner($beltAssetProcess){
    foreach($beltAssetMatch in [regex]::Matches($beltAssetProcess.CommandLine,'"([^"]+\.uproject)"|(\S+\.uproject)')){
        $beltAssetPath=if($beltAssetMatch.Groups[1].Success){$beltAssetMatch.Groups[1].Value}else{$beltAssetMatch.Groups[2].Value}
        if($beltAssetPath.Replace('\','/') -eq "$beltAssetProject/FPSGAME.uproject"){return $true}
    }
    $beltAssetModule=@((Get-Process -Id $beltAssetProcess.ProcessId -ErrorAction SilentlyContinue).Modules | Where-Object {$_.ModuleName -eq 'UnrealEditor-FPSGAME.dll'})
    return [bool]@($beltAssetModule | Where-Object {$_.FileName.Replace('\','/') -eq "$beltAssetProject/Binaries/Win64/UnrealEditor-FPSGAME.dll"}).Count
}
$beltAssetProcesses=@(Get-CimInstance Win32_Process)
$beltAssetEditor=@($beltAssetProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)' -and (Test-CombatBeltsIntegrationProjectOwner $_)})
if($beltAssetEditor.Count){
    $sportsWindow=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$sportsWindowHeld=$false
    try {
        # The nested bridge calls re-enter this same thread's mutex. End-play and
        # saving stay in one editor batch; no unrelated work runs under the gate.
        try{$sportsWindowHeld=$sportsWindow.WaitOne([TimeSpan]::FromSeconds(3600))}catch [Threading.AbandonedMutexException]{$sportsWindowHeld=$true}
        if(-not $sportsWindowHeld){throw 'Editor batch unavailable; no request sent.'}
        if($EndPlayAuthorized){
            & (Join-Path $beltAssetProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript (Join-Path $beltAssetProject 'Tools/WorkwearSet/end_play.py') -OutputFile (Join-Path $beltAssetLogs ($ReceiptName+'-end-play.txt')) -MaxOutputChars 700 -QueueWaitSeconds 60 -RequestTimeoutSeconds 120
            if($LASTEXITCODE -ne 0){throw 'End-play request failed; retain editor state.'}
        }
        & (Join-Path $beltAssetProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $beltAssetScript -OutputFile $beltAssetOutput -MaxOutputChars 2500 -QueueWaitSeconds 60 -RequestTimeoutSeconds 1800
        $sportsWindowExit=$LASTEXITCODE
        Save-CombatBeltsExecution $sportsWindowExit
    }finally{if($sportsWindowHeld){$sportsWindow.ReleaseMutex()};$sportsWindow.Dispose()}
    exit $sportsWindowExit
}
$beltAssetGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$beltAssetHeld=$false
try{
    Write-Output 'Queued for shared asset batch.'
    try{$beltAssetHeld=$beltAssetGate.WaitOne()}catch [Threading.AbandonedMutexException]{$beltAssetHeld=$true}
    while($true){
        $beltAssetBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and (Test-CombatBeltsIntegrationProjectOwner $_))
        })
        if(-not $beltAssetBusy.Count){break}
        if(@($beltAssetBusy | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)'}).Count){throw 'The project editor appeared; retain it and use the bridge on the next batch.'}
        Write-Output 'Waiting for the project engine/build owner.'
        try{Wait-Process -Id $beltAssetBusy[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $beltAssetBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    $beltAssetLog=Join-Path $beltAssetLogs ($ReceiptName+'.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$beltAssetProject/FPSGAME.uproject" '-run=pythonscript' "-script=$beltAssetScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' '-NoAssetRegistryCache' '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$beltAssetLog" *> $beltAssetOutput
    $beltAssetExit=$LASTEXITCODE;Save-CombatBeltsExecution $beltAssetExit;Write-Output "CombatBeltsIntegration commandlet exit=$beltAssetExit; log=$beltAssetLog";Get-Content -LiteralPath $beltAssetOutput -Tail 3;exit $beltAssetExit
}finally{if($beltAssetHeld){$beltAssetGate.ReleaseMutex()};$beltAssetGate.Dispose()}
