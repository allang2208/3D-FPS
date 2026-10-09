$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$outputRoot = "$projectRoot/SourceAssets/Super90ContinuousReload20261007"
# Wait for the existing native build to release the engine; do not compete
# for UBT's mutex or message another task.
Write-Output 'Waiting for existing native compilation to finish.'
do {
    $busy = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('cl.exe', 'link.exe', 'UnrealEditor-Cmd.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if ($busy.Count -gt 0) { Start-Sleep -Seconds 10 }
} while ($busy.Count -gt 0)
Write-Output 'Building FPSGAMEEditor in the background.'
& "$projectRoot/Tools/Build/Build-Editor.ps1" *> "$outputRoot/build_editor.log"
Write-Output 'Editor target built; importing and saving the continuous reload.'
& "$projectRoot/Tools/ModularOutfit/Run-Authoring.ps1" `
    -Script 'SourceAssets/Super90ContinuousReload20261007/import_reload.py' `
    -Log 'SourceAssets/Super90ContinuousReload20261007/import_commandlet.log' `
    *> "$outputRoot/import_console.log"
Write-Output 'Continuous reload asset saved. No gameplay testing was run.'
