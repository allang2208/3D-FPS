$ErrorActionPreference='Stop'
$warhammerRoot=$PSScriptRoot
$warhammerProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$warhammerBuild='E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
$warhammerReceipt=@()
foreach($warhammerTarget in @('FPSGAMEEditor','FPSGAME')) {
    if($warhammerTarget -eq 'FPSGAMEEditor' -and (Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'")) {
        throw 'Editor is running; preserve its current state. The base DLL build cannot proceed safely.'
    }
    $warhammerLog=Join-Path $warhammerRoot ('build-'+$warhammerTarget+'.log')
    [string[]]$warhammerExtraArgs=@()
    & $warhammerBuild $warhammerTarget Win64 Development ('-Project='+$warhammerProject) -NoHotReloadFromIDE -WaitMutex @warhammerExtraArgs *> $warhammerLog
    $warhammerExit=$LASTEXITCODE
    $warhammerReceipt+=@{target=$warhammerTarget;exit_code=$warhammerExit;extra_args=$warhammerExtraArgs;log=$warhammerLog;finished=(Get-Date).ToString('s')}
    $warhammerReceipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $warhammerRoot 'build_receipt.json') -Encoding utf8
    Write-Output ($warhammerTarget+' exit='+$warhammerExit)
    if($warhammerExit -ne 0){Get-Content -LiteralPath $warhammerLog -Tail 35;exit $warhammerExit}
}
