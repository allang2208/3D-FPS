$ErrorActionPreference='Stop'
$r=$PSScriptRoot
$old=Join-Path $r '../FreightCameraMatch20261113'
$bay=Join-Path $r '../FreightCartBay20261113'
if(!(Test-Path -LiteralPath "$r/DerivedDataCache")){New-Item -ItemType Junction -Path "$r/DerivedDataCache" -Target (Resolve-Path "$old/DerivedDataCache").Path | Out-Null}
Copy-Item -LiteralPath "$bay/photo_host.py" -Destination "$r/photo_host.py"
$run=(Get-Content "$old/render_host.ps1" -Raw).Replace("'-NoAssetRegistryCacheWrite'","'-NoAssetRegistryCacheWrite' '-AssetGatherAll=false'").Replace('$PSScriptRoot','$r')
& ([scriptblock]::Create($run)) -SceneScript photo_host.py
