param([string]$Blender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe')
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
Push-Location $project
try {
    & $Blender -b --python-exit-code 1 --python (Join-Path $PSScriptRoot 'author_arm_support.py') *> (Join-Path $PSScriptRoot 'authoring.log')
    if($LASTEXITCODE -ne 0){throw 'M870 arm authoring failed. See authoring.log; no import was started.'}
    & (Join-Path $PSScriptRoot 'install.ps1')
    & (Join-Path $PSScriptRoot '../M870ReloadContact20261016/rebuild.ps1') -Blender $Blender
    & (Join-Path $PSScriptRoot '../M870Super90Sprint20261016/rebuild.ps1') -Blender $Blender
    & (Join-Path $PSScriptRoot '../M870ReloadSource20261016/rebuild.ps1') -Blender $Blender
    & (Join-Path $PSScriptRoot '../M870TriggerGrip20261016/rebuild.ps1') -Blender $Blender
    & (Join-Path $PSScriptRoot '../M870LeftArm20261016/rebuild.ps1') -Blender $Blender
} finally {
    Pop-Location
}
