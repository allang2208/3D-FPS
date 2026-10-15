param([int]$Attempt=1)
$ErrorActionPreference = 'Stop'
$taskRoot = 'D:\FPS3D\FPSGAME\SourceAssets\WarhammerCommonRunes20261014'
$buildReceipts = @()
foreach ($buildTarget in @('FPSGAMEEditor','FPSGAME')) {
    $blocking = Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -match 'FPSGAME') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'cl.exe'
    }
    if ($blocking) { throw 'An editor or build is active; leave it running and defer this build.' }
    $buildLog = Join-Path $taskRoot ('build-'+$buildTarget+'-attempt'+$Attempt+'.log')
    & 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' $buildTarget Win64 Development '-Project=D:\FPS3D\FPSGAME\FPSGAME.uproject' -NoHotReloadFromIDE *> $buildLog
    $code = $LASTEXITCODE
    $buildReceipts += @{target=$buildTarget;exit_code=$code;log=$buildLog;finished=(Get-Date).ToString('s')}
    $buildReceipts | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot ('build_receipt-attempt'+$Attempt+'.json')) -Encoding UTF8
    if ($code -ne 0) { Get-Content -LiteralPath $buildLog -Tail 35; exit $code }
    Write-Output ($buildTarget+' build completed.')
}
