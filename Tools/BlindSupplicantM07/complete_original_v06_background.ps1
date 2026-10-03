param([switch]$RemakeSource)
$ErrorActionPreference = 'Stop'
$taskProjectRoot = 'D:/FPS3D/FPSGAME'
$taskTools = Join-Path $taskProjectRoot 'Tools/BlindSupplicantM07'
$taskSource = Join-Path $taskProjectRoot 'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV06'
$taskBlender = 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
$taskPython = 'C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe'

function Invoke-M07ProductionBlender([string]$Script, [string[]]$Arguments = @()) {
    & $taskBlender --background --python-exit-code 1 --python (Join-Path $taskTools $Script) -- @Arguments
    if ($LASTEXITCODE -ne 0) { throw "OriginalV06 Blender producer failed: $Script" }
}

if ($RemakeSource) {
    Invoke-M07ProductionBlender 'freeze_original_v06.py'
    & $taskPython (Join-Path $taskTools 'prepare_original_regions_v06.py')
    if ($LASTEXITCODE -ne 0) { throw 'OriginalV06 region authoring failed.' }
    & $taskPython (Join-Path $taskTools 'derive_original_gill_guides_v06.py')
    if ($LASTEXITCODE -ne 0) { throw 'OriginalV06 attachment authoring failed.' }
    Invoke-M07ProductionBlender 'author_original_rig_motion_v06.py'
    & $taskPython (Join-Path $taskTools 'prepare_original_weights_v06.py') --regions (Join-Path $taskSource 'regions/source_regions_original_v06.npz') --rig-guides (Join-Path $taskSource 'rig_motion/original_rig_guides.json')
    if ($LASTEXITCODE -ne 0) { throw 'OriginalV06 surface weights failed.' }
    Invoke-M07ProductionBlender 'author_original_surfaces_v06.py' @('--regions', (Join-Path $taskSource 'regions/source_regions_original_v06.npz'), '--rig', (Join-Path $taskSource 'rig_motion/M07_OriginalReference_Centimeter_V06.blend'))
    Invoke-M07ProductionBlender 'finish_original_source_v06.py'
}

# Required builds/import/save only. No GUI, PIE, simulation, render or tests.
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAMEEditor
& (Join-Path $taskTools 'run_import_background.ps1') -TaskScript (Join-Path $taskTools 'import_original_v06.py')
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAME
Write-Output 'OriginalV06 production executed. Actual save receipt: RecoveryOriginalV06/ue_original_delivery_v06.json. Untested; user review pending.'
