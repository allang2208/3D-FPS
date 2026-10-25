param([switch]$RefreshInputs, [switch]$RebuildTextures)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$assetRoot = Join-Path $projectRoot 'SourceAssets/TacticalMagazineBelt20261024'
$blenderExe = 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
Push-Location $projectRoot
try {
    if ($RefreshInputs) {
        & py -3.11 -X utf8 (Join-Path $PSScriptRoot 'prepare.py')
        if ($LASTEXITCODE -ne 0) { throw 'Could not refresh native waist sources.' }
    }
    if ($RebuildTextures -or -not (Test-Path -LiteralPath (Join-Path $assetRoot 'textures.json'))) {
        & py -3.11 -X utf8 (Join-Path $PSScriptRoot 'make_textures.py')
        if ($LASTEXITCODE -ne 0) { throw 'Surface authoring did not finish.' }
    }
    foreach ($bodyName in @('Jason', 'Kaitlin')) {
        $productionLog = Join-Path $assetRoot ('Logs/author-' + $bodyName + '.log')
        & $blenderExe -b --factory-startup -t 6 --python-exit-code 1 --python (Join-Path $PSScriptRoot 'author.py') -- $bodyName *> $productionLog
        if ($LASTEXITCODE -ne 0) { throw ('Model authoring stopped: ' + $productionLog) }
    }
} finally {
    Pop-Location
}
