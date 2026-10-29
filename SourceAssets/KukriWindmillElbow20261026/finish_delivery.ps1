param()
$ErrorActionPreference='Stop'
$kukriRoot='D:\FPS3D\FPSGAME'
$editors=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' })
if($editors.Count){throw 'An editor is running; no build submitted.'}
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development `
    ('-Project='+(Join-Path $kukriRoot 'FPSGAME.uproject')) -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 `
    ('-Log='+(Join-Path $PSScriptRoot 'build-editor.log')) *> (Join-Path $PSScriptRoot 'build-editor-console.log')
$kukriExit=$LASTEXITCODE
@{exit_code=$kukriExit;target='FPSGAMEEditor Win64 Development';completed=(Get-Date).ToString('o')} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build-editor-result.json') -Encoding UTF8
Get-Content -LiteralPath (Join-Path $PSScriptRoot 'build-editor-console.log') -Tail 16
if($kukriExit -ne 0){exit $kukriExit}
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'run_commandlet.ps1') -Stage save_and_preview
exit $LASTEXITCODE
