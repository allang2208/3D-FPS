param([string]$Blender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe')
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
Push-Location $project
try {
    & $Blender -b --python-exit-code 1 --python (Join-Path $PSScriptRoot 'author_source_reload.py') *> (Join-Path $PSScriptRoot 'authoring.log')
    if($LASTEXITCODE -ne 0){throw 'M870 source reload authoring failed; no import was started.'}
    & (Join-Path $PSScriptRoot 'install.ps1')
} finally { Pop-Location }
