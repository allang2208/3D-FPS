$ErrorActionPreference='Stop'
$detailRoot='D:/FPS3D/FPSGAME'
$detailOut="$detailRoot/SourceAssets/Saiga12KDetail20261018"
function DetailPhase([string]$phase){ @{phase=$phase;time=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$detailOut/Receipts/pipeline.json" -Encoding utf8 }
DetailPhase 'waiting_for_current_baseline'
while(-not (Test-Path -LiteralPath "$detailOut/Reports/baseline.json")){Start-Sleep -Seconds 10}
DetailPhase 'saving_private_assets'
& "$detailRoot/Tools/Saiga12KDetail/ue_step.ps1" -Step install_assets
DetailPhase 'reading_saved_assets'
& "$detailRoot/Tools/Saiga12KDetail/ue_step.ps1" -Step check_saved_assets
DetailPhase 'activating_saved_revision'
python "$detailRoot/Tools/Saiga12KDetail/activate.py"
if($LASTEXITCODE -ne 0){throw 'Asset activation failed'}
& "$detailRoot/Tools/Saiga12KDetail/ue_step.ps1" -Step import_icon
DetailPhase 'building_game_and_editor'
& "$detailRoot/Tools/Saiga12KDetail/build.ps1"
DetailPhase 'updating_catalogue'
& "$detailRoot/Tools/Saiga12KDetail/catalog.ps1"
DetailPhase 'assets_builds_catalogue_complete'
