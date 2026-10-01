param([string]$Weapon='')
$ErrorActionPreference='Stop'
$jobRoot=$PSScriptRoot
$manifest=Get-Content -LiteralPath (Join-Path $jobRoot 'manifest.json') -Raw | ConvertFrom-Json
$weapons=@($Weapon) # Empty means one headless production pass across all profiles.
foreach($entry in $weapons){
    @{weapon=$entry} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $jobRoot 'batch.json') -Encoding utf8
    & 'D:/FPS3D/FPSGAME/SourceAssets/WeaponSurface20260930/run_ue.ps1' -Script (Join-Path $jobRoot 'install_profiles.py')
    if($LASTEXITCODE -ne 0){throw "Asset batch did not complete: $entry"}
    Write-Output "ANIMATION_SHARING_WEAPON_SAVED $entry"
}
