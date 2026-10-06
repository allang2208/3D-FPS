$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/FPS3D/FPSGAME'
do {
    $taskEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" |
        Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject' })
    if ($taskEditors.Count) { Start-Sleep -Seconds 5 }
} while ($taskEditors.Count)
& "$taskRoot/Tools/ModularOutfit/Run-Authoring.ps1" `
    -Script 'SourceAssets/RSH12DualReloadDrop20261004/import_assets.py' `
    -Log 'SourceAssets/RSH12DualReloadDrop20261004/Import-commandlet.log'
& "$taskRoot/SourceAssets/RSH12DualReloadDrop20261004/build_editor.ps1"
