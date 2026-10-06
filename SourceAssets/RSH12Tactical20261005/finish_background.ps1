$ErrorActionPreference='Stop'
$taskOutput='D:/FPS3D/FPSGAME/SourceAssets/RSH12Tactical20261005'
& "$taskOutput/install_background.ps1"
if ($LASTEXITCODE -ne 0) {throw 'RSH tactical device asset installation did not complete.'}
& py -3.11 "$taskOutput/publish_catalog.py"
if ($LASTEXITCODE -ne 0) {throw 'RSH tactical device catalog publication did not complete.'}
& "$taskOutput/build_editor.ps1"
