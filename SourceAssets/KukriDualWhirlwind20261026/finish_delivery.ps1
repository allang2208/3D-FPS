param([int]$WaitForPackagingPid=0,[int]$QueueWaitSeconds=600)
$ErrorActionPreference='Stop'
$kukriRoot='D:\FPS3D\FPSGAME'
if($WaitForPackagingPid -gt 0 -and (Get-Process -Id $WaitForPackagingPid -ErrorAction SilentlyContinue)) {
    Wait-Process -Id $WaitForPackagingPid -Timeout $QueueWaitSeconds -ErrorAction Stop
}
$kukriBusy=@(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -or
    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool|BuildCookRun')
})
if($kukriBusy.Count){throw 'Existing editor or build/cook remains active; no build or asset operation submitted.'}
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development `
    ('-Project='+(Join-Path $kukriRoot 'FPSGAME.uproject')) -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 `
    ('-Log='+(Join-Path $PSScriptRoot 'build-editor.log')) *> (Join-Path $PSScriptRoot 'build-editor-console.log')
$kukriExit=$LASTEXITCODE
@{exit_code=$kukriExit;target='FPSGAMEEditor Win64 Development';completed=(Get-Date).ToString('o')} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build-editor-result.json') -Encoding UTF8
Get-Content -LiteralPath (Join-Path $PSScriptRoot 'build-editor-console.log') -Tail 12
if($kukriExit -ne 0){exit $kukriExit}
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'run_commandlet.ps1') -Stage save_all
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
$kukriSingle=Join-Path $kukriRoot 'SourceAssets\KukriWindmillDetail20261026'
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $kukriSingle 'run_commandlet.ps1') -Stage save_all
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
$kukriPython='C:\Users\allan\AppData\Local\Programs\Python\Python311\python.exe'
& $kukriPython (Join-Path $PSScriptRoot 'publish.py')
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $kukriPython (Join-Path $kukriSingle 'publish.py')
exit $LASTEXITCODE
