param([switch]$RebuildDelivery,[switch]$EndPlayAuthorized)
$ErrorActionPreference='Stop'
$beltProject='D:/FPS3D/FPSGAME'
$beltRoot=Join-Path $beltProject 'SourceAssets/TacticalMagazineBelt20261024'
$beltStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
if($RebuildDelivery -or -not (Test-Path -LiteralPath (Join-Path $beltRoot 'delivery.json'))) {
    & 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b --factory-startup -t 6 --python-exit-code 1 --python (Join-Path $PSScriptRoot 'prepare_delivery.py') *> (Join-Path $beltRoot ('Logs/prepare-delivery-'+$beltStamp+'.log'))
    if($LASTEXITCODE -ne 0){throw 'Belt delivery production incomplete'}
}
& (Join-Path $PSScriptRoot 'run_asset.ps1') -Script 'save_in_namespace.py' -ReceiptName ('belt-save-'+$beltStamp) -EndPlayAuthorized:$EndPlayAuthorized
if($LASTEXITCODE -ne 0){throw 'Belt asset save incomplete'}
& (Join-Path $PSScriptRoot 'build.ps1') -ReceiptName ('belt-build-'+$beltStamp)
if($LASTEXITCODE -ne 0){throw 'Belt code build incomplete'}
& py -3.11 -X utf8 (Join-Path $PSScriptRoot 'publish.py')
if($LASTEXITCODE -ne 0){throw 'Belt catalog publication incomplete'}
