$ErrorActionPreference = 'Stop'
$tangProject = 'D:\FPS3D\FPSGAME'
$tangSource = Join-Path $tangProject 'SourceAssets\TangDaoMeshy20261002'
$tangBuildExe = 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
$tangEditorCmd = 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
# Wait for already submitted native builds without competing for the UBT mutex.
while ($tangRunningBuilds = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' })) {
foreach ($tangRunningBuild in $tangRunningBuilds) {
    Write-Output ('TANGDAO_WAIT_EXISTING_BUILD ' + $tangRunningBuild.ProcessId)
    try { $tangProcess = Get-Process -Id $tangRunningBuild.ProcessId -ErrorAction Stop; $tangProcess.WaitForExit() } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { }
}
}
# Complete a scoped ordinary build. Do not start or restart the interactive editor.
if (Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('UnrealEditor.exe','FPSGAME.exe') -and $_.CommandLine -match 'FPSGAME[\\/]FPSGAME\.uproject' }) {
    throw 'An interactive editor or game is running; preserve it. Background DLL build is deferred.'
}
& $tangBuildExe FPSGAMEEditor Win64 Development ('-project=' + (Join-Path $tangProject 'FPSGAME.uproject')) -NoHotReloadFromIDE *> (Join-Path $tangSource 'build-editor.log')
$tangBuildExit = $LASTEXITCODE
Write-Output ('TANGDAO_BUILD_EXIT=' + $tangBuildExit)
if ($tangBuildExit -ne 0) { Get-Content -LiteralPath (Join-Path $tangSource 'build-editor.log') -Tail 45; exit $tangBuildExit }
& $tangEditorCmd (Join-Path $tangProject 'FPSGAME.uproject') -run=pythonscript ('-script=' + (Join-Path $tangSource 'import_tang_dao.py')) -nullrhi -unattended -nosplash -stdout '-ExecCmds=Interchange.FeatureFlags.Import.FBX 0' ('-abslog=' + (Join-Path $tangSource 'import-engine.log')) *> (Join-Path $tangSource 'import-commandlet.log')
$tangImportExit = $LASTEXITCODE
Write-Output ('TANGDAO_IMPORT_EXIT=' + $tangImportExit)
if ($tangImportExit -ne 0) { Get-Content -LiteralPath (Join-Path $tangSource 'import-commandlet.log') -Tail 40; exit $tangImportExit }
& $tangEditorCmd (Join-Path $tangProject 'FPSGAME.uproject') -run=pythonscript ('-script=' + (Join-Path $tangSource 'import_icons.py')) -nullrhi -unattended -nosplash -stdout ('-abslog=' + (Join-Path $tangSource 'icons-engine.log')) *> (Join-Path $tangSource 'icons-commandlet.log')
$tangIconsExit = $LASTEXITCODE
Write-Output ('TANGDAO_ICONS_EXIT=' + $tangIconsExit)
if ($tangIconsExit -ne 0) { Get-Content -LiteralPath (Join-Path $tangSource 'icons-commandlet.log') -Tail 40; exit $tangIconsExit }
