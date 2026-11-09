$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$jobs=Get-Content -LiteralPath "$root/settle_processes.json" | ConvertFrom-Json
do {
    $active=@($jobs.PSObject.Properties | Where-Object {Get-Process -Id $_.Value -ErrorAction SilentlyContinue})
    if($active.Count){Start-Sleep -Seconds 5}
}while($active.Count)
Write-Output 'CONTACT25_SETTLE_STAGE merge'
& py -3.11 "$root/merge_settle.py"
if($LASTEXITCODE){throw 'Settle contacts incomplete'}
& py -3.11 "$root/publish_profiles.py" *> "$root/publish_settled.log"
if($LASTEXITCODE){throw 'Settle authoring failed'}
& py -3.11 "$root/check_candidate.py" *> "$root/check_settled.log"
if($LASTEXITCODE){throw 'Settle pose checks failed'}
$auth=Get-Content -LiteralPath "$root/authoring.json" | ConvertFrom-Json
foreach($row in $auth.PSObject.Properties){
    if($row.Value.arm_length_error_cm -gt .001 -or $row.Value.outside_left_world_change -gt 1e-7){throw 'Bone length or non-left preservation failed'}
}
Write-Output 'CONTACT25_SETTLE_STAGE save'
& "$root/assets.ps1" -Script install.py
Write-Output 'CONTACT25_SETTLE_STAGE native capture'
& "$root/run.ps1" -Manifest manifest.json -Label settled
Write-Output 'CONTACT25_SETTLE_STAGE saved geometry'
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --threads 2 --python "$root/depths.py" -- settled *> "$root/depths_settled.log"
if($LASTEXITCODE){throw 'Native geometry review failed'}
& py -3.11 "$root/audit.py" settled *> "$root/audit_settled.log"
& py -3.11 "$root/sheets.py" settled *> "$root/sheets_settled.log"
& py -3.11 "$root/video.py" settled *> "$root/video_settled.log"
Write-Output 'CONTACT25_SETTLE_STAGE complete; inspect native images'
