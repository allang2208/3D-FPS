param([string]$ReceiptName='icon-import-01')
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$batchRoot=Join-Path $projectRoot 'SourceAssets/Super90IconReview20261016'
$scriptFile=Join-Path $batchRoot 'import_icons.py'
$outputFile=Join-Path $batchRoot ($ReceiptName+'.txt')
if(Test-Path -LiteralPath $outputFile){throw 'Use a fresh receipt name.'}
$processes=@(Get-CimInstance Win32_Process)
if(@($processes | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count -gt 0){
    & (Join-Path $projectRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $scriptFile -OutputFile $outputFile -MaxOutputChars 3000
    exit $LASTEXITCODE
}
if(@($processes | Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'Super90IconReview20261016'}).Count -gt 0){Write-Output 'Same batch is still running.';exit 75}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try{
    $held=$gate.WaitOne([TimeSpan]::FromSeconds(60))
    if(-not $held){Write-Output 'Asset batch queue timed out; no commandlet launched.';exit 75}
    $busy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
    if($busy.Count -gt 0){Write-Output 'Editor/build state changed while queued; no commandlet launched.';exit 75}
    $logFile=Join-Path $batchRoot ($ReceiptName+'.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' (Join-Path $projectRoot 'FPSGAME.uproject') '-run=pythonscript' "-script=$scriptFile" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' "-abslog=$logFile" *> $outputFile
    $result=$LASTEXITCODE
    Write-Output "Asset commandlet exit=$result; log=$logFile"
    Get-Content -LiteralPath $outputFile -Tail 10
    exit $result
}finally{
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
