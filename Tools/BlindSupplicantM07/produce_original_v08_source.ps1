$ErrorActionPreference = 'Stop'
$taskProjectRoot = 'D:/FPS3D/FPSGAME'
$taskTools = Join-Path $taskProjectRoot 'Tools/BlindSupplicantM07'
$taskSource = Join-Path $taskProjectRoot 'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV08'
$taskBlender = 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
$taskPython = 'C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe'

function Invoke-M07ProductionBlender([string]$Script, [string[]]$Arguments = @()) {
    & $taskBlender --background --python-exit-code 1 --python (Join-Path $taskTools $Script) -- @Arguments
    if ($LASTEXITCODE -ne 0) { throw "OriginalV08 Blender producer failed: $Script" }
}

# Hands, original UVs and organic back layers use the saved V07 authoring.
# Only the original biped legs, their weights and dependent exports change.
Invoke-M07ProductionBlender 'author_original_rig_motion_v08.py'
& $taskPython (Join-Path $taskTools 'prepare_original_weights_v08.py') --regions (Join-Path $taskSource 'regions/source_regions_original_v08.npz') --rig-guides (Join-Path $taskSource 'rig_motion/original_rig_guides.json')
if ($LASTEXITCODE -ne 0) { throw 'OriginalV08 original surface weights failed.' }
& $taskPython (Join-Path $taskTools 'author_biped_legs_v08.py') --rig-guides (Join-Path $taskSource 'rig_motion/original_rig_guides.json') --regions (Join-Path $taskSource 'regions/source_regions_original_v08.npz')
if ($LASTEXITCODE -ne 0) { throw 'OriginalV08 biped leg weights failed.' }
& $taskPython (Join-Path $taskTools 'merge_anatomical_weights_v08.py')
if ($LASTEXITCODE -ne 0) { throw 'OriginalV08 anatomical weight merge failed.' }
Invoke-M07ProductionBlender 'author_original_surfaces_v08.py' @('--regions', (Join-Path $taskSource 'regions/source_regions_original_v08.npz'), '--rig', (Join-Path $taskSource 'rig_motion/M07_OriginalReference_Centimeter_V08.blend'))
Invoke-M07ProductionBlender 'finish_original_source_v08.py'
Write-Output 'OriginalV08 editable source, original display, cloth source and 12 motions exported. UE assets not imported by this source-only producer.'
