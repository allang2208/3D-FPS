$ErrorActionPreference='Stop'
$r4Project='D:/FPS3D/FPSGAME'
$r4Root="$r4Project/SourceAssets/ModernTacticalSet20261113/CombatShirtR4"
while($true) {
    $r4Ready=$false
    try {
        $r4Ready=(Get-Content -LiteralPath "$r4Root/surface-finalized.json" -Raw | ConvertFrom-Json).completed -and (Get-Content -LiteralPath "$r4Root/collar-fitted.json" -Raw | ConvertFrom-Json).completed
    } catch { $r4Ready=$false }
    if($r4Ready){break}
    Start-Sleep -Seconds 10
}
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup -t 6 --python-exit-code 1 --python "$r4Project/Tools/ModernTacticalSet/combat4_sources.py" -- --vest-only *> "$r4Root/Logs/collar-artwork.log"
if($LASTEXITCODE -ne 0){throw 'Measured collar source/artwork production stopped'}
$env:TS01_R4_ART_KIND='vest'
& "$r4Project/Tools/ModernTacticalSet/combat4_stage_call.ps1" -Script "$r4Project/Tools/ModernTacticalSet/combat4_save_artwork.py" -Label 'artwork-final'
if($LASTEXITCODE -ne 0){throw 'Final R4 artwork save stopped'}
Write-Output 'R4_FINAL_ARTWORK_SAVED'
