$ErrorActionPreference='Stop'
$sportsRoot='D:/FPS3D/FPSGAME'
$sportsLogs=Join-Path $sportsRoot 'SourceAssets/SportsCap20261024/Logs'
[void](New-Item -ItemType Directory -Force -Path $sportsLogs)
& py -3.11 (Join-Path $sportsRoot 'Tools/SportsCap/make_textures.py')
if($LASTEXITCODE -ne 0){throw 'Sports cap texture production failed.'}
$sportsLog=Join-Path $sportsLogs ('author-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b --factory-startup -t 6 --python-exit-code 1 --python (Join-Path $sportsRoot 'Tools/SportsCap/author.py') *> $sportsLog
if($LASTEXITCODE -ne 0){Get-Content -LiteralPath $sportsLog -Tail 25;throw 'Sports cap authoring stopped; preserve the completed exports.'}
Get-Content -LiteralPath $sportsLog -Tail 8
