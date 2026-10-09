$ErrorActionPreference='Stop'
$taskPython='C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe'
$taskBlender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
& $taskPython (Join-Path $PSScriptRoot 'prepare_signs.py')
if ($LASTEXITCODE -ne 0) { throw 'Route label authoring failed' }
& $taskBlender --background --python (Join-Path $PSScriptRoot 'author_entry.py') --python (Join-Path $PSScriptRoot 'author_signs.py') --python (Join-Path $PSScriptRoot 'author_relocated_sign.py')
if ($LASTEXITCODE -ne 0) { throw 'Entry geometry export failed' }
& $taskPython (Join-Path $PSScriptRoot 'extend_catalog.py')
if ($LASTEXITCODE -ne 0) { throw 'Facility recipe preparation failed' }
