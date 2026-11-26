param([string]$Plan='authored.json')
$ErrorActionPreference='Stop'
$r4Project='D:/FPS3D/FPSGAME'
$r4Root="$r4Project/SourceAssets/ModernTacticalSet20261113/CombatShirtR4"
$env:TS01_R4_SAVE_PLAN="$r4Root/$Plan"
$env:TS01_R4_BATCH_SIZE='6'
$r4Rows=(Get-Content -LiteralPath $env:TS01_R4_SAVE_PLAN -Raw | ConvertFrom-Json).rows.Count
for($r4Batch=0;$r4Batch -le [Math]::Ceiling($r4Rows/6);$r4Batch++) {
    & "$r4Project/Tools/ModernTacticalSet/combat4_stage_call.ps1" -Script "$r4Project/Tools/ModernTacticalSet/combat4_save.py" -Label "wear-$r4Batch"
    if($LASTEXITCODE -ne 0){throw 'R4 asset save stopped; preserve receipts and resume the same plan'}
    $r4Saved=Get-Content -LiteralPath "$r4Root/saved.json" -Raw | ConvertFrom-Json
    if($r4Saved.completed){Write-Output 'R4_ALL_SKELETAL_PACKAGES_SAVED';exit 0}
}
throw 'R4 save plan has unfinished packages'
