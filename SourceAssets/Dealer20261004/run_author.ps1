param(
    [string]$Python='C:/Users/allan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
    [string]$Blender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
)
$ErrorActionPreference='Stop'
& $Python (Join-Path $PSScriptRoot 'author_art.py')
if($LASTEXITCODE -ne 0){throw 'Dealer artwork production failed.'}
& $Python (Join-Path $PSScriptRoot 'AudioV3/author_audio.py')
if($LASTEXITCODE -ne 0){throw 'Dealer laugh production failed.'}
& $Blender -b -t 4 --python-exit-code 1 --python (Join-Path $PSScriptRoot 'author_model.py') *> (Join-Path $PSScriptRoot 'author-model.log')
if($LASTEXITCODE -ne 0){throw 'Dealer model production failed; see author-model.log.'}
Write-Output 'DEALER_SOURCE_SAVED textures=3 models=2 deck=52 preview=false'
