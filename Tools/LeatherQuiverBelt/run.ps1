param([switch]$RebuildTextures,[string[]]$Bodies=@('Jason','Kaitlin'))
$ErrorActionPreference='Stop'
$quiverProject=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$quiverRoot=Join-Path $quiverProject 'SourceAssets/LeatherQuiverBelt20261025'
Push-Location $quiverProject
try {
    if($RebuildTextures -or -not (Test-Path -LiteralPath (Join-Path $quiverRoot 'textures.json'))){
        & py -3.11 -X utf8 (Join-Path $PSScriptRoot 'make_textures.py')
        if($LASTEXITCODE -ne 0){throw 'Leather surface production failed'}
    }
    foreach($quiverBody in $Bodies){
        $quiverLog=Join-Path $quiverRoot ('Logs/author-'+$quiverBody+'.log')
        & 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b --factory-startup -t 6 --python-exit-code 1 --python (Join-Path $PSScriptRoot 'author.py') -- $quiverBody *> $quiverLog
        if($LASTEXITCODE -ne 0){Get-Content -LiteralPath $quiverLog -Tail 24;throw ('Model production stopped: '+$quiverBody)}
        Write-Output ('LEATHER_QUIVER_SAVED '+$quiverBody)
    }
} finally {Pop-Location}
