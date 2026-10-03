param([switch]$RemakeSource)
$ErrorActionPreference='Stop'
$taskProjectRoot='D:/FPS3D/FPSGAME'
$taskTools=Join-Path $taskProjectRoot 'Tools/BlindSupplicantM07'
if ($RemakeSource) {
    & 'C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe' (Join-Path $taskTools 'prepare_gill_weights_v09.py')
    if ($LASTEXITCODE -ne 0) { throw 'V09 original gill weight producer failed.' }
    foreach ($taskScript in @('author_original_gills_v09.py','finish_original_gills_v09.py')) {
        & 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python-exit-code 1 --python (Join-Path $taskTools $taskScript)
        if ($LASTEXITCODE -ne 0) { throw "V09 gill source producer failed: $taskScript" }
    }
}
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAMEEditor
& (Join-Path $taskTools 'run_import_background.ps1') -TaskScript (Join-Path $taskTools 'import_original_gills_v09.py')
$taskReceipt=Get-Content -LiteralPath (Join-Path $taskProjectRoot 'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV09/ue_gill_delivery_v09.json') -Raw | ConvertFrom-Json
if (-not $taskReceipt.saved) { throw 'V09 new assets not saved; native display defaults left on V08.' }
$taskNativeFile=Join-Path $taskProjectRoot 'Source/FPSGAME/Monsters/BlindSupplicantMonster.cpp'
$taskNativeSource=[IO.File]::ReadAllText($taskNativeFile)
# Only the display path changes. V08 rig/action/navigation contracts stay.
[IO.File]::WriteAllText($taskNativeFile,$taskNativeSource.Replace('SK_M07_OriginalV08','SK_M07_OriginalV09'),[Text.UTF8Encoding]::new($false))
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAMEEditor
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAME
Write-Output 'V09 gill source and AI/F6 display reference saved; V08 actions and navigation retained. No GUI, game or test was started.'
