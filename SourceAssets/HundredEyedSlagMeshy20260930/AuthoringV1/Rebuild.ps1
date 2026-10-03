$ErrorActionPreference = 'Stop'
$TaskBlender = 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
foreach ($TaskScript in @('prepare_mesh.py', 'rig_and_animate.py', 'export_delivery.py')) {
    & $TaskBlender --background --factory-startup --python-exit-code 1 --python (Join-Path $PSScriptRoot $TaskScript)
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

