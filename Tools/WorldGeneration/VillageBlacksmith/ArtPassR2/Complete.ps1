# One queued, owned batch. Each UE phase runs in a fresh process for asset readback.
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$out=Join-Path $project 'SourceAssets/HillsVillageBlacksmith20261117/ArtPassR2'
$batchGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$batchHeld=$false
function Write-BatchState([string]$stage,[string]$status) {
    @{stage=$stage;status=$status;updated=(Get-Date -Format o);interactive_editor_started=$false;gameplay_started=$false}|
        ConvertTo-Json|Set-Content -LiteralPath "$out/batch-status.json" -Encoding utf8
}
try {
    Write-BatchState 'queue' 'waiting_for_existing_ue_batch'
    try{$batchHeld=$batchGate.WaitOne([TimeSpan]::FromMinutes(5))}catch [Threading.AbandonedMutexException]{$batchHeld=$true}
    if(-not $batchHeld){throw 'Existing UE batch remains occupied; preserved the pending production batch without changing assets.'}
    foreach($phase in @(@('read_inputs.py','inputs'),@('import_assets.py','import'),@('publish_revision.py','publish'),@('review_saved.py','review'))) {
        Write-BatchState $phase[1] 'running'
        if($phase[1] -eq 'review'){& "$PSScriptRoot/Run.ps1" -Script $phase[0] -Stage $phase[1] -Render}
        else{& "$PSScriptRoot/Run.ps1" -Script $phase[0] -Stage $phase[1]}
        $receipt=Get-Content -LiteralPath "$out/$($phase[1])-process.json" -Raw|ConvertFrom-Json
        if($receipt.exit_code -ne 0){throw "UE phase $($phase[1]) failed with $($receipt.exit_code)"}
    }
    Write-BatchState 'review' 'completed'
}catch{Write-BatchState 'error' $_.Exception.Message;throw}
finally{if($batchHeld){$batchGate.ReleaseMutex()};$batchGate.Dispose()}
