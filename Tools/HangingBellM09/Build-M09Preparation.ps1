$ErrorActionPreference = 'Stop'
$m09ProjectRoot = 'D:\FPS3D\FPSGAME'
$m09Python = 'C:\Users\allan\AppData\Local\Programs\Python\Python311\python.exe'
$m09Blender = 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
& $m09Python (Join-Path $m09ProjectRoot 'Tools\HangingBellM09\prepare_source.py')
if ($LASTEXITCODE -ne 0) { throw 'M09 source preparation failed.' }
& $m09Python (Join-Path $m09ProjectRoot 'Tools\HangingBellM09\author_semantic_parts.py')
if ($LASTEXITCODE -ne 0) { throw 'M09 semantic authoring failed.' }
& $m09Blender --background --factory-startup --python-exit-code 1 --python (Join-Path $m09ProjectRoot 'Tools\HangingBellM09\build_adjusted_parts_blender.py')
if ($LASTEXITCODE -ne 0) { throw 'M09 Blender authoring/export failed.' }
