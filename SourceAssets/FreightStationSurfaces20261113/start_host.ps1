$ErrorActionPreference='Stop'
$r=$PSScriptRoot
$old=Join-Path $r '../FreightCameraMatch20261113'
if(!(Test-Path -LiteralPath "$r/DerivedDataCache")){New-Item -ItemType Junction -Path "$r/DerivedDataCache" -Target (Resolve-Path "$old/DerivedDataCache").Path | Out-Null}
$run=(Get-Content "$old/render_host.ps1" -Raw).Replace("'-NoAssetRegistryCacheWrite'","'-NoAssetRegistryCacheWrite' '-AssetGatherAll=false'").Replace("'-AllowCommandletRendering' '-RenderOffscreen' '-d3d12'","'-nullrhi'").Replace('$PSScriptRoot','$r')
& ([scriptblock]::Create($run)) -SceneScript author_host.py
