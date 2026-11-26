param([switch]$ResumeSave)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$toolsRoot = Join-Path $projectRoot 'Tools/BackpackFit'
$fitRoot = Join-Path $projectRoot 'SourceAssets/BackpackFit20261024/ModernTacticalShoulders20261118'
$env:BACKPACK_FIT_RUN_DIR = $fitRoot
$env:BACKPACK_FIT_SHIRT = 'ue_modern_kevlar_vest'
$env:BACKPACK_FIT_NEW_ASSETS_ONLY = '1'
$stage = Join-Path $PSScriptRoot 'shoulder_stage.ps1'
$blender = 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
New-Item -ItemType Directory -Force -Path $fitRoot | Out-Null
if (!$ResumeSave) {
    & python -X utf8 (Join-Path $toolsRoot 'pending.py')
    if ($LASTEXITCODE) { throw 'Could not determine garment and backpack inputs' }
    $pending = Get-Content -LiteralPath "$fitRoot/pending.json" -Raw | ConvertFrom-Json
    if ($pending.count -eq 0) { return }
    if (!(Test-Path -LiteralPath "$fitRoot/captured.json")) {
        Copy-Item -LiteralPath (Join-Path $fitRoot '../ModernTacticalShirtR420261115/captured.json') -Destination "$fitRoot/captured.json"
    }
    & $stage -Script (Join-Path $toolsRoot 'capture.py') -Label 'backpack-capture'
    & python -X utf8 (Join-Path $toolsRoot 'classify_cargo.py')
    if ($LASTEXITCODE) { throw 'Could not classify cargo islands' }
    foreach ($step in @('surfaces','sample_shells')) {
        & $blender --factory-startup -b -t 6 --python-exit-code 1 --python (Join-Path $toolsRoot "$step.py") *> "$fitRoot/$step.log"
        if ($LASTEXITCODE) { throw "Backpack geometry stage $step failed" }
    }
    & python -X utf8 (Join-Path $toolsRoot 'author_contact.py') *> "$fitRoot/author.log"
    if ($LASTEXITCODE) { throw 'Could not author backpack contact geometry' }
}
$inputCount = (Get-Content -LiteralPath "$fitRoot/authored.json" -Raw | ConvertFrom-Json)
$batchSize = 12
$env:BACKPACK_FIT_BATCH_SIZE = "$batchSize"
$batches = [math]::Ceiling(($inputCount.rows.Count+$inputCount.statics.Count)/$batchSize)
for ($batch=0; $batch -lt $batches; $batch++) {
    & $stage -Script (Join-Path $toolsRoot 'save_assets.py') -Label "backpack-save-$batch"
    $saved = Get-Content -LiteralPath "$fitRoot/saved_assets.json" -Raw | ConvertFrom-Json
    if ($saved.completed) { break }
}
if (!$saved.completed) { throw 'Backpack assets incomplete' }
foreach ($step in @('publish','register')) {
    & python -X utf8 (Join-Path $toolsRoot "$step.py")
    if ($LASTEXITCODE) { throw "Backpack $step failed" }
}
