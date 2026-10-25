param([string]$Script='save.py',[string]$ReceiptName=('waist-'+(Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference='Stop'
$waistProject='D:/FPS3D/FPSGAME'
$waistLogs=Join-Path $waistProject 'SourceAssets/GarmentWaist20261023/Logs'
[void](New-Item -ItemType Directory -Force -Path $waistLogs)
$waistScript=Join-Path $waistProject ('Tools/GarmentWaist/'+$Script)
$waistOutput=Join-Path $waistLogs ($ReceiptName+'.txt')
if(Test-Path -LiteralPath $waistOutput){throw 'Use a fresh waist receipt name.'}
function Test-WaistProjectOwner($waistProcess){
    foreach($waistMatch in [regex]::Matches($waistProcess.CommandLine,'"([^"]+\.uproject)"|(\S+\.uproject)')){
        $waistPath=if($waistMatch.Groups[1].Success){$waistMatch.Groups[1].Value}else{$waistMatch.Groups[2].Value}
        if($waistPath.Replace('\','/') -eq "$waistProject/FPSGAME.uproject"){return $true}
    }
    $waistModule=@((Get-Process -Id $waistProcess.ProcessId -ErrorAction SilentlyContinue).Modules | Where-Object {$_.ModuleName -eq 'UnrealEditor-FPSGAME.dll'})
    return [bool]@($waistModule | Where-Object {$_.FileName.Replace('\','/') -eq "$waistProject/Binaries/Win64/UnrealEditor-FPSGAME.dll"}).Count
}
$waistProcesses=@(Get-CimInstance Win32_Process)
$waistEditor=@($waistProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)' -and (Test-WaistProjectOwner $_)})
if($waistEditor.Count){
    & (Join-Path $waistProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $waistScript -OutputFile $waistOutput -MaxOutputChars 2500 -QueueWaitSeconds 3600 -RequestTimeoutSeconds 1800
    exit $LASTEXITCODE
}
$waistGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$waistHeld=$false
try{
    Write-Output 'Queued for shared asset batch.'
    try{$waistHeld=$waistGate.WaitOne()}catch [Threading.AbandonedMutexException]{$waistHeld=$true}
    while($true){
        $waistBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and (Test-WaistProjectOwner $_))
        })
        if(-not $waistBusy.Count){break}
        if(@($waistBusy | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)'}).Count){throw 'The project editor appeared; retain it and use the bridge on the next batch.'}
        Write-Output 'Waiting for the project engine/build owner.'
        try{Wait-Process -Id $waistBusy[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $waistBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    $waistLog=Join-Path $waistLogs ($ReceiptName+'.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$waistProject/FPSGAME.uproject" '-run=pythonscript' "-script=$waistScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$waistLog" *> $waistOutput
    $waistExit=$LASTEXITCODE;Write-Output "Waist commandlet exit=$waistExit; log=$waistLog";Get-Content -LiteralPath $waistOutput -Tail 3;exit $waistExit
}finally{if($waistHeld){$waistGate.ReleaseMutex()};$waistGate.Dispose()}
