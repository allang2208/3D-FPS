$ErrorActionPreference = 'Stop'
$blenderExe = 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
$pipelinePython = 'D:/FPS3D/FPSGAME/Saved/HandBrainVenv/Scripts/python.exe'
# Reuse downloaded Hunyuan geometry. This does not submit paid cloud jobs.
foreach ($step in @('prepare_body.py','assemble_rig.py','add_crown.py','validate_rig_poses.py','animate_export.py','validate_delivery.py','export_ue_textures.py','render_animations.py','render_fbx_proof.py')) {
    & $blenderExe --background --factory-startup --python-exit-code 1 --python (Join-Path $PSScriptRoot $step)
    if ($LASTEXITCODE -ne 0) { throw "Pipeline failed: $step" }
}
& $pipelinePython (Join-Path $PSScriptRoot 'package_previews.py')
if ($LASTEXITCODE -ne 0) { throw 'Preview packaging failed' }
