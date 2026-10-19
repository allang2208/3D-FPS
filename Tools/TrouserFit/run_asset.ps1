param([string]$Script='save_assets.py',[string]$ReceiptName='asset-save-01')
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$batchRoot=Join-Path $projectRoot 'SourceAssets/TrouserFit20261018'
$scriptFile=Join-Path $projectRoot ('Tools/TrouserFit/'+$Script)
$outputFile=Join-Path $batchRoot ($ReceiptName+'.txt')
if(Test-Path -LiteralPath $outputFile){throw 'Use a fresh receipt name.'}
$processes=@(Get-CimInstance Win32_Process)
$editor=@($processes | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)'})
if($editor.Count){
    & (Join-Path $projectRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $scriptFile -OutputFile $outputFile -MaxOutputChars 2500 -QueueWaitSeconds 3600 -RequestTimeoutSeconds 900
    exit $LASTEXITCODE
}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try{
    Write-Output 'Queued for shared asset batch; keeping one pending mutex wait.'
    try{$held=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    while($true){
        $busy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build\.bat')})
        if(-not $busy.Count){break}
        if(@($busy | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)'}).Count){Write-Output 'Editor opened while queued; retry with the bridge.';exit 75}
        Write-Output 'Waiting for existing engine/build process.'
        try{Wait-Process -Id $busy[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $busy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    $logFile=Join-Path $batchRoot ($ReceiptName+'.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' (Join-Path $projectRoot 'FPSGAME.uproject') '-run=pythonscript' "-script=$scriptFile" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' "-abslog=$logFile" *> $outputFile
    $result=$LASTEXITCODE;Write-Output "Asset commandlet exit=$result; log=$logFile";Get-Content -LiteralPath $outputFile -Tail 8;exit $result
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
