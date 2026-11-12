$ErrorActionPreference='Stop'
$review=Join-Path $PSScriptRoot '../Wrist34'
& "$review/run-native.ps1" -Mode geometry -Label geometry_wrist_thirty_eight_final -Manifest '../Wrist37/FollowupReview/manifest.json'
if($LASTEXITCODE -ne 0){throw 'Final geometry capture failed'}
& "$review/run-native.ps1" -Mode native -Label native_wrist_thirty_eight_final
if($LASTEXITCODE -ne 0){throw 'Final continuity check failed'}
& "$PSScriptRoot/run-wire.ps1" -SkipBuild -Port 19998
if($LASTEXITCODE -ne 0){throw 'Final two-peer capture failed'}
