$ErrorActionPreference='Stop'
$st6Root='D:/FPS3D/FPSGAME'
$st6Stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
for($st6Batch=1;$st6Batch -le 6;$st6Batch++){
    & (Join-Path $st6Root 'Tools/ST6LowerDetail/run_asset.ps1') -Script save_assets.py -ReceiptName ('lower-detail-'+$st6Stamp+'-'+$st6Batch)
    if($LASTEXITCODE -ne 0){throw 'ST6 lower detail save batch failed; retain saved assets and inspect the batch log.'}
    $st6Receipt=Get-Content -LiteralPath (Join-Path $st6Root 'SourceAssets/ST6LowerDetail20261024/saved_assets.json') -Raw | ConvertFrom-Json
    Write-Output ('ST6 lower detail remaining='+$st6Receipt.remaining)
    if($st6Receipt.completed){Write-Output 'ST6 lower detail assets complete.';exit 0}
}
throw 'ST6 production exceeded the planned six save batches.'