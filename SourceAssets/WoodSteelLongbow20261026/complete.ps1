param([int]$PendingImporterPid=0,[switch]$UseExistingBuilds)
$ErrorActionPreference='Stop'
$bowStateFile=Join-Path $PSScriptRoot 'completion.json'
function Save-BowStage([string]$Stage,[string]$Detail='') {
    @{stage=$Stage;detail=$Detail;updated=(Get-Date).ToString('s');gameplay_tested=$false} |
        ConvertTo-Json | Set-Content -LiteralPath $bowStateFile -Encoding utf8
}
try {
    Save-BowStage 'waiting_for_asset_batch'
    if($PendingImporterPid -gt 0){
        while(Get-Process -Id $PendingImporterPid -ErrorAction SilentlyContinue){Start-Sleep -Seconds 5}
    }
    $bowSaved=$false
    $bowReceipt=Join-Path $PSScriptRoot 'import-receipt.json'
    $bowIcons=Join-Path $PSScriptRoot 'icon-import-receipt.json'
    if((Test-Path -LiteralPath $bowReceipt) -and (Test-Path -LiteralPath $bowIcons)){
        $bowSaved=(Get-Content -LiteralPath $bowReceipt -Raw|ConvertFrom-Json).complete -and
            (Get-Content -LiteralPath $bowIcons -Raw|ConvertFrom-Json).complete
    }
    if(-not $bowSaved){
        & (Join-Path $PSScriptRoot 'run_stage.ps1') -QueueWaitSeconds 86400
        if($LASTEXITCODE -ne 0){throw "Asset publishing stopped with exit code $LASTEXITCODE"}
    }
    Save-BowStage 'building'
    if($UseExistingBuilds){
        & python (Join-Path $PSScriptRoot 'record_existing_builds.py')
    } else {
        & (Join-Path $PSScriptRoot 'build.ps1')
    }
    if($LASTEXITCODE -ne 0){throw "Build stopped with exit code $LASTEXITCODE"}
    Save-BowStage 'saving_weapon_catalog'
    & python (Join-Path $PSScriptRoot 'install_catalog.py')
    if($LASTEXITCODE -ne 0){throw "Catalog installation stopped with exit code $LASTEXITCODE"}
    Save-BowStage 'complete' 'Assets, catalogs, Editor and Game binaries saved. Gameplay remains untested.'
    Write-Output 'WOOD_STEEL_LONGBOW_COMPLETE'
} catch {
    Save-BowStage 'stopped' $_.Exception.Message
    throw
}
