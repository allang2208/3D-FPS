$ErrorActionPreference='Stop'
$kukriProject='D:\FPS3D\FPSGAME'
$kukriBuild='E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
$kukriReceipts=@()
foreach($kukriTarget in @('FPSGAME','FPSGAMEEditor')) {
    $kukriBusy=@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if($kukriBusy.Count){throw 'A native build is active; no competing build was submitted.'}
    $kukriOwners=@(Get-CimInstance Win32_Process | Where-Object {
        ($kukriTarget -eq 'FPSGAMEEditor' -and $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe')) -or
        ($kukriTarget -eq 'FPSGAME' -and $_.Name -eq 'FPSGAME.exe')
    })
    if($kukriOwners.Count){throw "The $kukriTarget binary is in use; no process was closed."}
    $kukriLog=Join-Path $PSScriptRoot ('build-'+$kukriTarget+'.log')
    & $kukriBuild $kukriTarget Win64 Development ('-Project='+(Join-Path $kukriProject 'FPSGAME.uproject')) `
        -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 ('-Log='+$kukriLog) `
        *> (Join-Path $PSScriptRoot ('build-'+$kukriTarget+'-console.log'))
    $kukriCode=$LASTEXITCODE
    $kukriReceipts+=@{target=$kukriTarget;exit_code=$kukriCode;completed=(Get-Date).ToString('o');log=$kukriLog}
    $kukriReceipts | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build-receipt.json') -Encoding utf8
    Get-Content -LiteralPath (Join-Path $PSScriptRoot ('build-'+$kukriTarget+'-console.log')) -Tail 12
    if($kukriCode -ne 0){exit $kukriCode}
}
