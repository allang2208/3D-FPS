param([string]$Script='save_assets.py',[string]$ReceiptName=('workwear-'+(Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference='Stop'
$workwearProject='D:/FPS3D/FPSGAME'
$workwearLogs=Join-Path $workwearProject 'SourceAssets/WorkwearSet20261024/Logs'
[void](New-Item -ItemType Directory -Force -Path $workwearLogs)
$workwearScript=Join-Path $workwearProject ('Tools/WorkwearSet/'+$Script)
$workwearOutput=Join-Path $workwearLogs ($ReceiptName+'.txt')
if(Test-Path -LiteralPath $workwearOutput){throw 'Use a fresh workwear receipt name.'}
function Test-WorkwearProjectOwner($workwearProcess){
    foreach($workwearMatch in [regex]::Matches($workwearProcess.CommandLine,'"([^"]+\.uproject)"|(\S+\.uproject)')){
        $workwearPath=if($workwearMatch.Groups[1].Success){$workwearMatch.Groups[1].Value}else{$workwearMatch.Groups[2].Value}
        if($workwearPath.Replace('\','/') -eq "$workwearProject/FPSGAME.uproject"){return $true}
    }
    $workwearModule=@((Get-Process -Id $workwearProcess.ProcessId -ErrorAction SilentlyContinue).Modules | Where-Object {$_.ModuleName -eq 'UnrealEditor-FPSGAME.dll'})
    return [bool]@($workwearModule | Where-Object {$_.FileName.Replace('\','/') -eq "$workwearProject/Binaries/Win64/UnrealEditor-FPSGAME.dll"}).Count
}
$workwearProcesses=@(Get-CimInstance Win32_Process)
$workwearEditor=@($workwearProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)' -and (Test-WorkwearProjectOwner $_)})
if($workwearEditor.Count){
    & (Join-Path $workwearProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $workwearScript -OutputFile $workwearOutput -MaxOutputChars 2500 -QueueWaitSeconds 3600 -RequestTimeoutSeconds 1800
    exit $LASTEXITCODE
}
$workwearGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$workwearHeld=$false
try{
    Write-Output 'Queued for shared asset batch.'
    try{$workwearHeld=$workwearGate.WaitOne()}catch [Threading.AbandonedMutexException]{$workwearHeld=$true}
    while($true){
        $workwearBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and (Test-WorkwearProjectOwner $_))
        })
        if(-not $workwearBusy.Count){break}
        if(@($workwearBusy | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)'}).Count){throw 'The project editor appeared; retain it and use the bridge on the next batch.'}
        Write-Output 'Waiting for the project engine/build owner.'
        try{Wait-Process -Id $workwearBusy[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $workwearBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    $workwearLog=Join-Path $workwearLogs ($ReceiptName+'.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$workwearProject/FPSGAME.uproject" '-run=pythonscript' "-script=$workwearScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$workwearLog" *> $workwearOutput
    $workwearExit=$LASTEXITCODE;Write-Output "Workwear commandlet exit=$workwearExit; log=$workwearLog";Get-Content -LiteralPath $workwearOutput -Tail 3;exit $workwearExit
}finally{if($workwearHeld){$workwearGate.ReleaseMutex()};$workwearGate.Dispose()}
