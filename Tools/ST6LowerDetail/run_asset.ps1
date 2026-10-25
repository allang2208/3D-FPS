param([string]$Script='save_assets.py',[string]$ReceiptName=('lowerDetail-'+(Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference='Stop'
$lowerDetailProject='D:/FPS3D/FPSGAME'
$lowerDetailLogs=Join-Path $lowerDetailProject 'SourceAssets/ST6LowerDetail20261024/Logs'
[void](New-Item -ItemType Directory -Force -Path $lowerDetailLogs)
$lowerDetailScript=Join-Path $lowerDetailProject ('Tools/ST6LowerDetail/'+$Script)
$lowerDetailOutput=Join-Path $lowerDetailLogs ($ReceiptName+'.txt')
if(Test-Path -LiteralPath $lowerDetailOutput){throw 'Use a fresh lowerDetail receipt name.'}
function Test-LowerDetailProjectOwner($lowerDetailProcess){
    foreach($lowerDetailMatch in [regex]::Matches($lowerDetailProcess.CommandLine,'"([^"]+\.uproject)"|(\S+\.uproject)')){
        $lowerDetailPath=if($lowerDetailMatch.Groups[1].Success){$lowerDetailMatch.Groups[1].Value}else{$lowerDetailMatch.Groups[2].Value}
        if($lowerDetailPath.Replace('\','/') -eq "$lowerDetailProject/FPSGAME.uproject"){return $true}
    }
    $lowerDetailModule=@((Get-Process -Id $lowerDetailProcess.ProcessId -ErrorAction SilentlyContinue).Modules | Where-Object {$_.ModuleName -eq 'UnrealEditor-FPSGAME.dll'})
    return [bool]@($lowerDetailModule | Where-Object {$_.FileName.Replace('\','/') -eq "$lowerDetailProject/Binaries/Win64/UnrealEditor-FPSGAME.dll"}).Count
}
$lowerDetailProcesses=@(Get-CimInstance Win32_Process)
$lowerDetailEditor=@($lowerDetailProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)' -and (Test-LowerDetailProjectOwner $_)})
if($lowerDetailEditor.Count){
    & (Join-Path $lowerDetailProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $lowerDetailScript -OutputFile $lowerDetailOutput -MaxOutputChars 2500 -QueueWaitSeconds 3600 -RequestTimeoutSeconds 1800
    exit $LASTEXITCODE
}
$lowerDetailGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$lowerDetailHeld=$false
try{
    Write-Output 'Queued for shared asset batch.'
    try{$lowerDetailHeld=$lowerDetailGate.WaitOne()}catch [Threading.AbandonedMutexException]{$lowerDetailHeld=$true}
    while($true){
        $lowerDetailBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and (Test-LowerDetailProjectOwner $_))
        })
        if(-not $lowerDetailBusy.Count){break}
        if(@($lowerDetailBusy | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)'}).Count){throw 'The project editor appeared; retain it and use the bridge on the next batch.'}
        Write-Output 'Waiting for the project engine/build owner.'
        try{Wait-Process -Id $lowerDetailBusy[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $lowerDetailBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    $lowerDetailLog=Join-Path $lowerDetailLogs ($ReceiptName+'.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$lowerDetailProject/FPSGAME.uproject" '-run=pythonscript' "-script=$lowerDetailScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$lowerDetailLog" *> $lowerDetailOutput
    $lowerDetailExit=$LASTEXITCODE;Write-Output "LowerDetail commandlet exit=$lowerDetailExit; log=$lowerDetailLog";Get-Content -LiteralPath $lowerDetailOutput -Tail 3;exit $lowerDetailExit
}finally{if($lowerDetailHeld){$lowerDetailGate.ReleaseMutex()};$lowerDetailGate.Dispose()}
