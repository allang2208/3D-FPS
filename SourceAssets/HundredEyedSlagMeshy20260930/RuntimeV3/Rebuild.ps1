param([ValidateSet('All','Authoring','Install')][string]$Stage='All')
$ErrorActionPreference='Stop'
if($Stage -ne 'Install') {
    foreach($script in @('prepare_runtime.py','author_runtime.py','bake_surface.py')) {
        & 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --python-exit-code 1 --python (Join-Path $PSScriptRoot $script)
        if($LASTEXITCODE -ne 0){throw ('Authoring failed: '+$script)}
    }
}
if($Stage -ne 'Authoring') { & (Join-Path $PSScriptRoot 'Finish-Background.ps1') -IncludeMeshes }
