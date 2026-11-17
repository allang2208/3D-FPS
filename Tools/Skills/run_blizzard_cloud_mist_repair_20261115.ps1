$ErrorActionPreference='Stop'
$blizzardRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$blizzardOut=Join-Path $blizzardRoot 'SourceAssets/BlizzardCloudMistRepair20261115'
$blizzardScript=Join-Path $PSScriptRoot 'repair_blizzard_cloud_mist_20261115.py'
while ($true) {
    $blizzardStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $blizzardEditors=@(Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue | Where-Object {$_.Threads.Count -gt 0})
    if ($blizzardEditors.Count) {
        & (Join-Path $blizzardRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $blizzardScript `
            -OutputFile (Join-Path $blizzardOut ('repair-'+$blizzardStamp+'.log')) -MaxOutputChars 1800 -QueueWaitSeconds 60
        if ($LASTEXITCODE -ne 0) {throw 'Blizzard repair bridge failed; preserve current assets and read its receipt.'}
    } else {
        & (Join-Path $PSScriptRoot 'run_meteor_visibility_background.ps1') -MainProject -Script $blizzardScript `
            -Stage 'cloud-mist-repair' -OutputRoot $blizzardOut
    }
    $blizzardState=Get-Content -LiteralPath (Join-Path $blizzardOut 'status.json') -Raw | ConvertFrom-Json
    if ($blizzardState.state -eq 'saved') {Write-Output 'BLIZZARD_CLOUD_MIST_REPAIR_COMPLETE';break}
    if ($blizzardState.state -ne 'waiting_for_pie_end') {throw 'Unexpected Blizzard author state'}
    Start-Sleep -Seconds 20
}
