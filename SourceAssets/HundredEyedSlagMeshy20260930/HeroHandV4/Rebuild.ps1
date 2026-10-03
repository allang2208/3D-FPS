param([ValidateSet('All','Authoring','Install')][string]$Stage='All')
$ErrorActionPreference='Stop'
if($Stage -ne 'Install') {
    & 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --python-exit-code 1 --python (Join-Path $PSScriptRoot 'author_hero_hand.py')
    if($LASTEXITCODE -ne 0){throw 'Hero hand authoring failed.'}
}
if($Stage -ne 'Authoring') { & (Join-Path $PSScriptRoot 'Finish-Background.ps1') }
