$ErrorActionPreference='Stop'
$headRoot=$PSScriptRoot
$headProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$headBuild='E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
$headReceipt=@()
foreach($headTarget in @('FPSGAMEEditor','FPSGAME')) {
    while($headBusy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' })) {
        foreach($headProcess in $headBusy) {try {Wait-Process -Id $headProcess.ProcessId -ErrorAction Stop} catch [Microsoft.PowerShell.Commands.ProcessCommandException] {}}
    }
    if($headTarget -eq 'FPSGAMEEditor' -and (Get-Process UnrealEditor -ErrorAction SilentlyContinue)){throw 'Editor is open; preserve it and defer the base Editor DLL build.'}
    $headLog=Join-Path $headRoot ('build-'+$headTarget+'.log')
    & $headBuild $headTarget Win64 Development ('-Project='+$headProject) -NoHotReloadFromIDE *> $headLog
    $headExit=$LASTEXITCODE
    $headReceipt+=@{target=$headTarget;exit_code=$headExit;log=$headLog;finished=(Get-Date).ToString('s')}
    $headReceipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $headRoot 'build_receipt.json') -Encoding utf8
    if($headExit -ne 0){Get-Content -LiteralPath $headLog -Tail 25;exit $headExit}
    Write-Output ($headTarget+' build completed')
}
