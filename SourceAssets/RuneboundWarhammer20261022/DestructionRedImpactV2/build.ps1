param([string[]]$Targets=@('FPSGAMEEditor','FPSGAME'), [string]$Attempt='01')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$ubt = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll'
$project = Join-Path $projectRoot 'FPSGAME.uproject'
$pending = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' })
if ($pending.Count -gt 0) {
    Write-Output 'Waiting for the existing native build before submitting this build.'
    foreach ($buildProcess in $pending) {
        Wait-Process -Id $buildProcess.ProcessId -ErrorAction SilentlyContinue
    }
}
$receipt = @{targets=@(); attempts=@(); tests_run=$false; game_started=$false; editor_ui_started=$false}
$receiptPath = Join-Path $PSScriptRoot 'build_receipt.json'
if (Test-Path -LiteralPath $receiptPath) {
    $previous = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
    $receipt.targets = @($previous.targets)
    if ($previous.attempts) {$receipt.attempts = @($previous.attempts)}
}
foreach ($target in $Targets) {
    $logPath = Join-Path $PSScriptRoot ('build-' + $target + '-' + $Attempt + '.log')
    & dotnet $ubt $target Win64 Development "-Project=$project" -WaitMutex -NoHotReloadFromIDE -MaxParallelActions=4 "-log=$logPath"
    $resultCode = $LASTEXITCODE
    $binary = Join-Path $projectRoot $(if ($target -eq 'FPSGAMEEditor') {'Binaries/Win64/UnrealEditor-FPSGAME.dll'} else {'Binaries/Win64/FPSGAME.exe'})
    $receipt.attempts += @($receipt.targets | Where-Object {$_.target -eq $target})
    $receipt.targets = @($receipt.targets | Where-Object {$_.target -ne $target})
    $receipt.targets += @{target=$target;exit_code=$resultCode;log=$logPath;binary=$binary;binary_written_at=$(if(Test-Path -LiteralPath $binary){(Get-Item -LiteralPath $binary).LastWriteTime.ToString('o')}else{$null})}
    $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
    if ($resultCode -ne 0) {exit $resultCode}
}
exit 0
