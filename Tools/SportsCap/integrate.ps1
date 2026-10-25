$ErrorActionPreference='Stop'
$sportsRoot='D:/FPS3D/FPSGAME'
$sportsStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$sportsLog=Join-Path $sportsRoot ('SourceAssets/SportsCap20261024/Logs/prepare-delivery-'+$sportsStamp+'.log')
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b --factory-startup -t 6 --python-exit-code 1 --python (Join-Path $sportsRoot 'Tools/SportsCap/prepare_delivery.py') *> $sportsLog
if($LASTEXITCODE -ne 0){Get-Content -LiteralPath $sportsLog -Tail 15;throw 'Sports cap inventory production stopped.'}
& (Join-Path $sportsRoot 'Tools/SportsCap/run_asset.ps1') -Script 'save_in_namespace.py' -ReceiptName ('sports-cap-save-'+$sportsStamp)
if($LASTEXITCODE -ne 0){throw 'Sports cap asset save incomplete; retain saved progress.'}
& py -3.11 -X utf8 (Join-Path $sportsRoot 'Tools/SportsCap/publish.py')
if($LASTEXITCODE -ne 0){throw 'Sports cap scoped publication incomplete.'}
