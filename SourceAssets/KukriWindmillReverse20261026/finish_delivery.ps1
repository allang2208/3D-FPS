param([int]$WaitBuildId=0)
$ErrorActionPreference='Stop'
if($WaitBuildId -gt 0 -and (Get-Process -Id $WaitBuildId -ErrorAction SilentlyContinue)){
    Wait-Process -Id $WaitBuildId -ErrorAction SilentlyContinue
}
$kukriRoot='D:\FPS3D\FPSGAME'
$busy=@(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^UnrealEditor(-Cmd)?\.exe$|UnrealBuildTool|^cl.exe$|^link.exe$' -or
    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
})
if($busy.Count){throw 'Another editor or native build is active; no build submitted.'}
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development `
    ('-Project='+(Join-Path $kukriRoot 'FPSGAME.uproject')) -NoHotReload -NoHotReloadFromIDE -NoUBA `
    ('-Log='+(Join-Path $PSScriptRoot 'build-editor.log')) *> (Join-Path $PSScriptRoot 'build-editor-console.log')
$kukriExit=$LASTEXITCODE
@{exit_code=$kukriExit;target='FPSGAMEEditor Win64 Development';completed=(Get-Date).ToString('o')} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build-editor-result.json') -Encoding UTF8
Get-Content -LiteralPath (Join-Path $PSScriptRoot 'build-editor-console.log') -Tail 16
if($kukriExit -ne 0){exit $kukriExit}
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'run_commandlet.ps1') -Stage resume_save_after_pie
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& 'C:\Users\allan\AppData\Local\Programs\Python\Python311\python.exe' (Join-Path $PSScriptRoot 'publish.py')
exit $LASTEXITCODE
