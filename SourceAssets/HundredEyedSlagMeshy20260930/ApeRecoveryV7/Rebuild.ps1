param([ValidateSet('All','Authoring','Install')][string]$Stage='All')
$ErrorActionPreference='Stop'
if ($Stage -ne 'Install') {
    & 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --python-exit-code 1 --python (Join-Path $PSScriptRoot 'author_ape_recovery.py')
    if ($LASTEXITCODE -ne 0) { throw 'Heavy-arm authoring failed.' }
}
if ($Stage -ne 'Authoring') { & (Join-Path $PSScriptRoot 'Finish-Background.ps1') }
