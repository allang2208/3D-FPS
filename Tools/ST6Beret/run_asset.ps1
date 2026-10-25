param([string]$Script='save_assets.py',[string]$ReceiptName=('beret-'+(Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference='Stop'
$beretProject='D:/FPS3D/FPSGAME'
$beretLogs=Join-Path $beretProject 'SourceAssets/ST6Beret20261023/SurfaceV2/Logs'
[void](New-Item -ItemType Directory -Force -Path $beretLogs)
$beretScript=Join-Path $beretProject ('Tools/ST6Beret/'+$Script)
$beretOutput=Join-Path $beretLogs ($ReceiptName+'.txt')
if(Test-Path -LiteralPath $beretOutput){throw 'Use a fresh beret receipt name.'}
function Test-BeretProjectOwner($beretProcess){
    foreach($beretMatch in [regex]::Matches($beretProcess.CommandLine,'"([^"]+\.uproject)"|(\S+\.uproject)')){
        $beretPath=if($beretMatch.Groups[1].Success){$beretMatch.Groups[1].Value}else{$beretMatch.Groups[2].Value}
        if($beretPath.Replace('\','/') -eq "$beretProject/FPSGAME.uproject"){return $true}
    }
    $beretModule=@((Get-Process -Id $beretProcess.ProcessId -ErrorAction SilentlyContinue).Modules | Where-Object {$_.ModuleName -eq 'UnrealEditor-FPSGAME.dll'})
    return [bool]@($beretModule | Where-Object {$_.FileName.Replace('\','/') -eq "$beretProject/Binaries/Win64/UnrealEditor-FPSGAME.dll"}).Count
}
$beretProcesses=@(Get-CimInstance Win32_Process)
$beretEditor=@($beretProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)' -and (Test-BeretProjectOwner $_)})
if($beretEditor.Count){
    & (Join-Path $beretProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $beretScript -OutputFile $beretOutput -MaxOutputChars 2500 -QueueWaitSeconds 3600 -RequestTimeoutSeconds 1800
    exit $LASTEXITCODE
}
$beretGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$beretHeld=$false
try{
    Write-Output 'Queued for shared asset batch.'
    try{$beretHeld=$beretGate.WaitOne()}catch [Threading.AbandonedMutexException]{$beretHeld=$true}
    while($true){
        $beretBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and (Test-BeretProjectOwner $_))
        })
        if(-not $beretBusy.Count){break}
        if(@($beretBusy | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)'}).Count){throw 'The project editor appeared; retain it and use the bridge on the next batch.'}
        Write-Output 'Waiting for the project engine/build owner.'
        try{Wait-Process -Id $beretBusy[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $beretBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    $beretLog=Join-Path $beretLogs ($ReceiptName+'.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$beretProject/FPSGAME.uproject" '-run=pythonscript' "-script=$beretScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$beretLog" *> $beretOutput
    $beretExit=$LASTEXITCODE;Write-Output "Beret commandlet exit=$beretExit; log=$beretLog";Get-Content -LiteralPath $beretOutput -Tail 3;exit $beretExit
}finally{if($beretHeld){$beretGate.ReleaseMutex()};$beretGate.Dispose()}
