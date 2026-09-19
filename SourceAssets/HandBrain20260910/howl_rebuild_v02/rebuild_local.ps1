$ErrorActionPreference = 'Stop'
$taskBlender = 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
$taskPython = 'D:/FPS3D/FPSGAME/Saved/HandBrainVenv/Scripts/python.exe'
foreach ($taskScript in @('build_single_face.py', 'animate_export.py', 'validate.py', 'verify_fbx.py', 'export_materials.py', 'render_preview.py')) {
    & $taskBlender --background --factory-startup --python-exit-code 1 --python (Join-Path $PSScriptRoot $taskScript)
    if ($LASTEXITCODE -ne 0) { throw "$taskScript failed: $LASTEXITCODE" }
}
& $taskPython (Join-Path $PSScriptRoot 'validate_glb.py')
if ($LASTEXITCODE -ne 0) { throw 'GLB validation failed' }
& $taskPython (Join-Path $PSScriptRoot 'package_preview.py')
if ($LASTEXITCODE -ne 0) { throw 'Preview packaging failed' }
