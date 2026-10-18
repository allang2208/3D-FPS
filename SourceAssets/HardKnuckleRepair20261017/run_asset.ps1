param([string]$ReceiptName='asset-import-01',[string]$Script='import_assets.py')
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$batchRoot=Join-Path $projectRoot 'SourceAssets/HardKnuckleRepair20261017'
$scriptFile=Join-Path $batchRoot $Script
$outputFile=Join-Path $batchRoot ($ReceiptName+'.txt')
if(Test-Path -LiteralPath $outputFile){throw 'Use a fresh receipt name.'}
$processes=@(Get-CimInstance Win32_Process)
if(@($processes | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count -gt 0){
    & (Join-Path $projectRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $scriptFile -OutputFile $outputFile -MaxOutputChars 3000
    exit $LASTEXITCODE
}
if(@($processes | Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'HardKnuckleRepair20261017'}).Count -gt 0){Write-Output 'Same batch is still running.';exit 75}
while($true){
    $active=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build\.bat')})
    if(-not $active.Count){break}
    Write-Output 'Waiting for the existing build before asset work.'
    try{Wait-Process -Id $active[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $active[0].ProcessId -ErrorAction SilentlyContinue){throw}}
}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try{
    while(-not $held){
        try{$held=$gate.WaitOne([TimeSpan]::FromSeconds(45))}catch [Threading.AbandonedMutexException]{$held=$true}
        if(-not $held){Write-Output 'Waiting for the shared asset batch.'}
    }
    while($true){
        $busy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if(-not $busy.Count){break}
        if(@($busy | Where-Object Name -eq 'UnrealEditor.exe').Count -gt 0){Write-Output 'Editor opened while queued; preserve it and use the bridge.';exit 75}
        Write-Output 'A build started while queued; waiting for it to finish.'
        try{Wait-Process -Id $busy[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $busy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
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
