param([string[]]$Targets=@('FPSGAME','FPSGAMEEditor'),[string]$Attempt='01')
$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$ubt='E:/Program Files (x86)/UE_5.8/Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll'
$project=Join-Path $projectRoot 'FPSGAME.uproject'
$pending=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'})
foreach($runningBuild in $pending){Wait-Process -Id $runningBuild.ProcessId -ErrorAction SilentlyContinue}
$receipt=@{targets=@();attempts=@();tests_run=$false;game_started=$false;editor_ui_started=$false}
$receiptPath=Join-Path $PSScriptRoot 'build_receipt.json'
if(Test-Path -LiteralPath $receiptPath){
    $previous=Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
    $receipt.targets=@($previous.targets)
    if($previous.attempts){$receipt.attempts=@($previous.attempts)}
}
foreach($target in $Targets){
    if($target -eq 'FPSGAMEEditor'){
        $holders=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -match '^UnrealEditor(?:-Cmd)?\.exe$' -and $_.CommandLine -match [regex]::Escape($project)})
        foreach($holder in $holders){Wait-Process -Id $holder.ProcessId -ErrorAction SilentlyContinue}
    }
    $log=Join-Path $PSScriptRoot ('build-'+$target+'-'+$Attempt+'.log')
    $activeBuilds=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'})
    foreach($activeBuild in $activeBuilds){Wait-Process -Id $activeBuild.ProcessId -ErrorAction SilentlyContinue}
    & dotnet $ubt $target Win64 Development "-Project=$project" -WaitMutex -NoHotReloadFromIDE -MaxParallelActions=4 "-log=$log"
    $code=$LASTEXITCODE
    $binary=Join-Path $projectRoot $(if($target -eq 'FPSGAMEEditor'){'Binaries/Win64/UnrealEditor-FPSGAME.dll'}else{'Binaries/Win64/FPSGAME.exe'})
    $receipt.attempts+=@($receipt.targets | Where-Object {$_.target -eq $target})
    $receipt.targets=@($receipt.targets | Where-Object {$_.target -ne $target})
    $receipt.targets+=@{target=$target;exit_code=$code;log=$log;binary=$binary;written_at=$(if(Test-Path -LiteralPath $binary){(Get-Item -LiteralPath $binary).LastWriteTime.ToString('o')}else{$null})}
    $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
    if($code -ne 0){exit $code}
}
exit 0
