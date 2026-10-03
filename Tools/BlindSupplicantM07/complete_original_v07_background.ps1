param([switch]$RemakeSource)
$ErrorActionPreference = 'Stop'
$taskProjectRoot = 'D:/FPS3D/FPSGAME'
$taskTools = Join-Path $taskProjectRoot 'Tools/BlindSupplicantM07'
$taskSource = Join-Path $taskProjectRoot 'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV07'
$taskBlender = 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
$taskPython = 'C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe'

function Invoke-M07ProductionBlender([string]$Script, [string[]]$Arguments = @()) {
    & $taskBlender --background --python-exit-code 1 --python (Join-Path $taskTools $Script) -- @Arguments
    if ($LASTEXITCODE -ne 0) { throw "OriginalV07 Blender producer failed: $Script" }
}

if ($RemakeSource) {
    New-Item -ItemType Directory -Path (Join-Path $taskSource 'regions'),(Join-Path $taskSource 'rig_motion') -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $taskProjectRoot 'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV06/regions/source_regions_original_v06.npz') -Destination (Join-Path $taskSource 'regions/source_regions_original_v07.npz')
    & $taskPython (Join-Path $taskTools 'author_hand_anatomy_v07.py')
    if ($LASTEXITCODE -ne 0) { throw 'OriginalV07 hand authoring failed.' }
    & $taskPython (Join-Path $taskTools 'author_hindlegs_v07.py')
    if ($LASTEXITCODE -ne 0) { throw 'OriginalV07 hindleg authoring failed.' }
    & $taskPython (Join-Path $taskTools 'author_gill_surface_v07.py')
    if ($LASTEXITCODE -ne 0) { throw 'OriginalV07 original gill surface authoring failed.' }
    Invoke-M07ProductionBlender 'author_original_rig_motion_v07.py'
    & $taskPython (Join-Path $taskTools 'prepare_original_weights_v07.py') --regions (Join-Path $taskSource 'regions/source_regions_original_v07.npz') --rig-guides (Join-Path $taskSource 'rig_motion/original_rig_guides.json')
    if ($LASTEXITCODE -ne 0) { throw 'OriginalV07 surface weights failed.' }
    & $taskPython (Join-Path $taskTools 'author_hindlegs_v07.py') --rig-guides (Join-Path $taskSource 'rig_motion/original_rig_guides.json') --regions (Join-Path $taskSource 'regions/source_regions_original_v07.npz')
    if ($LASTEXITCODE -ne 0) { throw 'OriginalV07 final hindleg weights failed.' }
    & $taskPython (Join-Path $taskTools 'merge_anatomical_weights_v07.py')
    if ($LASTEXITCODE -ne 0) { throw 'OriginalV07 anatomical weight merge failed.' }
    Invoke-M07ProductionBlender 'author_original_surfaces_v07.py' @('--regions', (Join-Path $taskSource 'regions/source_regions_original_v07.npz'), '--rig', (Join-Path $taskSource 'rig_motion/M07_OriginalReference_Centimeter_V07.blend'))
    Invoke-M07ProductionBlender 'finish_original_source_v07.py'
}

# Required builds/import/save only. No GUI, PIE, simulation, render or tests.
# The native CDO must not request a new asset before its first import. The
# saved V06 baseline supplies constructor dependencies during production.
$taskNativeCpp = Join-Path $taskProjectRoot 'Source/FPSGAME/Monsters/BlindSupplicantMonster.cpp'
$taskNativeSource = [IO.File]::ReadAllText($taskNativeCpp)
[IO.File]::WriteAllText($taskNativeCpp, $taskNativeSource.Replace('SK_M07_OriginalV07','SK_M07_OriginalV06').Replace('AnimationsOriginalV07','AnimationsOriginalV06'), [Text.UTF8Encoding]::new($false))
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAMEEditor
& (Join-Path $taskTools 'run_import_background.ps1') -TaskScript (Join-Path $taskTools 'import_original_v07.py')
$taskNativeSource = [IO.File]::ReadAllText($taskNativeCpp)
[IO.File]::WriteAllText($taskNativeCpp, $taskNativeSource.Replace('SK_M07_OriginalV06','SK_M07_OriginalV07').Replace('AnimationsOriginalV06','AnimationsOriginalV07'), [Text.UTF8Encoding]::new($false))
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAMEEditor
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAME
Write-Output 'OriginalV07 production executed. Actual save receipt: RecoveryOriginalV07/ue_original_delivery_v07.json. Untested; user review pending.'
