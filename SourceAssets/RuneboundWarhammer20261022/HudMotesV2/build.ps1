param([string[]]$Targets=@('FPSGAME','FPSGAMEEditor'), [string]$Attempt='01')
$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$project=Join-Path $projectRoot 'FPSGAME.uproject'
$ubt='E:/Program Files (x86)/UE_5.8/Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll'
$pending=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'})
if($pending.Count -gt 0){Write-Output 'Waiting for the current native build.';foreach($process in $pending){Wait-Process -Id $process.ProcessId -ErrorAction SilentlyContinue}}
$receipt=@{targets=@();attempts=@();tests_run=$false;game_started=$false;editor_ui_started=$false}
$receiptPath=Join-Path $PSScriptRoot 'build_receipt.json'
if(Test-Path -LiteralPath $receiptPath){$old=Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json;$receipt.targets=@($old.targets);if($old.attempts){$receipt.attempts=@($old.attempts)}}
foreach($target in $Targets){
    if($target -eq 'FPSGAMEEditor'){
        $holders=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match '[\\/]FPSGAME\.uproject'})
        if(@($holders | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count -gt 0){throw 'The main editor holds the native DLL; preserve its session.'}
        if($holders.Count -gt 0){Write-Output 'Waiting for the existing main-project commandlet to release the Editor module.';foreach($process in $holders){Wait-Process -Id $process.ProcessId -ErrorAction SilentlyContinue}}
    }
    $logPath=Join-Path $PSScriptRoot ('build-'+$target+'-'+$Attempt+'.log')
    & dotnet $ubt $target Win64 Development "-Project=$project" -WaitMutex -NoHotReloadFromIDE -MaxParallelActions=4 "-log=$logPath"
    $code=$LASTEXITCODE
    $binary=Join-Path $projectRoot $(if($target -eq 'FPSGAMEEditor'){'Binaries/Win64/UnrealEditor-FPSGAME.dll'}else{'Binaries/Win64/FPSGAME.exe'})
    $receipt.attempts+=@($receipt.targets | Where-Object {$_.target -eq $target})
    $receipt.targets=@($receipt.targets | Where-Object {$_.target -ne $target})
    $receipt.targets+=@{target=$target;exit_code=$code;log=$logPath;binary=$binary;binary_written_at=$(if(Test-Path -LiteralPath $binary){(Get-Item -LiteralPath $binary).LastWriteTime.ToString('o')}else{$null})}
    $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
    if($code -ne 0){exit $code}
}
exit 0
