$ErrorActionPreference='Stop'
$r4Project='D:/FPS3D/FPSGAME'
$r4Root="$r4Project/SourceAssets/ModernTacticalSet20261113/CombatShirtR4"
while($true) {
    $r4Ready=$false
    try {
        $r4Saved=Get-Content -LiteralPath "$r4Root/saved.json" -Raw | ConvertFrom-Json
        $r4Art=Get-Content -LiteralPath "$r4Root/artwork-saved.json" -Raw | ConvertFrom-Json
        $r4Surface=Get-Content -LiteralPath "$r4Root/surface-finalized.json" -Raw | ConvertFrom-Json
        $r4Collar=Get-Content -LiteralPath "$r4Root/collar-artwork.json" -Raw | ConvertFrom-Json
        $r4Ready=$r4Saved.completed -and $r4Art.completed -and $r4Surface.completed -and $r4Collar.completed -and $r4Saved.manifest.Replace('\','/').EndsWith('/authored.json') -and (@($r4Saved.wear.PSObject.Properties).Count -eq 98)
    } catch { $r4Ready=$false }
    if($r4Ready){break}
    Start-Sleep -Seconds 10
}
& python -X utf8 "$r4Project/Tools/ModernTacticalSet/combat4_publish.py"
if($LASTEXITCODE -ne 0){throw 'R4 clothing publication stopped'}
& "$r4Project/Tools/ModernTacticalSet/combat4_backpack.ps1"
if($LASTEXITCODE -ne 0){throw 'R4 backpack integration stopped'}
& python -X utf8 "$r4Project/Tools/ModernTacticalSet/combat4_complete.py"
if($LASTEXITCODE -ne 0){throw 'R4 completion receipt stopped'}
Write-Output 'R4_ALL_REQUESTED_PRODUCTION_AND_INTEGRATION_COMPLETE'
