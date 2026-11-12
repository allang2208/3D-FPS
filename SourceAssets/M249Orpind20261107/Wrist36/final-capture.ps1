$ErrorActionPreference='Stop'
$review=Join-Path $PSScriptRoot '../Wrist34'
& "$review/run-native.ps1" -Mode geometry -Label geometry_wrist_thirty_six_delivered -Manifest '../Wrist36/manifest_geometry.json'
if($LASTEXITCODE -ne 0){throw 'Final geometry capture failed'}
& "$review/run-native.ps1" -Mode native -Label native_wrist_thirty_six_delivered
if($LASTEXITCODE -ne 0){throw 'Final continuity capture failed'}
& "$PSScriptRoot/run-wire.ps1" -SkipBuild -Port 19997
if($LASTEXITCODE -ne 0){throw 'Final network capture failed'}
