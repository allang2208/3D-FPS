param(
 [string]$BlenderExe = 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe',
 [string]$PythonExe = 'C:\Users\allan\AppData\Local\Programs\Python\Python311\python.exe'
)
$ErrorActionPreference = 'Stop'
$rigRoot = 'D:\FPS3D\FPSGAME\SourceAssets\HangingBellM09Meshy20261003\RigV03'
$toolRoot = $PSScriptRoot
New-Item -ItemType Directory -Path "$rigRoot\Records" -Force | Out-Null
& $BlenderExe --background --factory-startup --python-exit-code 1 --python "$toolRoot\extract_rig_input_blender.py" *> "$rigRoot\Records\extract.log"
if ($LASTEXITCODE -ne 0) { throw 'M09 rig input extraction failed; see Records\extract.log.' }
& $PythonExe "$toolRoot\author_rig_weights_v03.py" *> "$rigRoot\Records\skin_authoring.log"
if ($LASTEXITCODE -ne 0) { throw 'M09 skin authoring failed; see Records\skin_authoring.log.' }
& $BlenderExe --background --factory-startup --python-exit-code 1 --python "$toolRoot\build_rigged_blender_v03.py" *> "$rigRoot\Records\rig_build.log"
if ($LASTEXITCODE -ne 0) { throw 'M09 rig save/export failed; see Records\rig_build.log.' }
Write-Output "M09 Rig V03 saved: $rigRoot"
