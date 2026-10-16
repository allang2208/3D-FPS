param(
    [string]$BlenderExe = 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe',
    [string]$PythonExe = 'C:\Users\allan\AppData\Local\Programs\Python\Python311\python.exe'
)
$ErrorActionPreference = 'Stop'
$potionModelRoot = Split-Path -Parent $PSScriptRoot
$potionReceipts = Join-Path $potionModelRoot 'Receipts'
New-Item -ItemType Directory -Path $potionReceipts -Force | Out-Null
& $BlenderExe --background --factory-startup --python-exit-code 1 --python (Join-Path $PSScriptRoot 'prepare_sources.py') *> (Join-Path $potionReceipts 'source-preparation.log')
if ($LASTEXITCODE -ne 0) { throw 'Wood material extraction failed.' }
& $PythonExe (Join-Path $PSScriptRoot 'prepare_textures.py') *> (Join-Path $potionReceipts 'texture-authoring.log')
if ($LASTEXITCODE -ne 0) { throw 'PBR texture authoring failed.' }
& $BlenderExe --background --factory-startup --python-exit-code 1 --python (Join-Path $PSScriptRoot 'author_workbench.py') *> (Join-Path $potionReceipts 'authoring.log')
if ($LASTEXITCODE -ne 0) { throw 'Workbench authoring/export failed; see authoring.log.' }
Write-Output 'Potion workbench source model and exports saved. No render, tests or UE launch performed.'
