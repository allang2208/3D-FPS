$ErrorActionPreference = 'Stop'
$taskBlender = 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
foreach ($taskScript in @('build_death.py', 'render_verify.py')) {
    & $taskBlender --background --factory-startup --python-exit-code 1 --python (Join-Path $PSScriptRoot $taskScript)
    if ($LASTEXITCODE -ne 0) { throw "$taskScript failed" }
}
& 'D:/FPS3D/FPSGAME/Saved/HandBrainVenv/Scripts/python.exe' (Join-Path $PSScriptRoot 'package_preview.py')
if ($LASTEXITCODE -ne 0) { throw 'Preview packaging failed' }
