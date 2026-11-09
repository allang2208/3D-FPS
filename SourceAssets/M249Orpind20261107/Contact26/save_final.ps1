$ErrorActionPreference='Stop'
$jobs=@(Get-Content -LiteralPath "$PSScriptRoot/protected2_processes.json" -Raw | ConvertFrom-Json)
$jobs+=Get-Content -LiteralPath "$PSScriptRoot/prism_protected_process.json" -Raw | ConvertFrom-Json
do {
 $active=@($jobs | Where-Object { Get-Process -Id $_.pid -ErrorAction SilentlyContinue })
 if($active.Count){Start-Sleep -Seconds 5}
} while($active.Count)
foreach($job in $jobs){
 $messages=@(Select-String -LiteralPath "$PSScriptRoot/$($job.family).protected2.log" -SimpleMatch 'CONTACT_PROTECTED')
 if($messages.Count -ne 2){throw "Incomplete contact pass: $($job.family)"}
}
& py -3.11 "$PSScriptRoot/merge_protected.py"
if($LASTEXITCODE -ne 0){throw 'Contact merge failed'}
& py -3.11 "$PSScriptRoot/publish_profiles.py"
if($LASTEXITCODE -ne 0){throw 'Profile authoring failed'}
& "$PSScriptRoot/assets.ps1" -Script 'install.py'
$receipt=Get-Content -LiteralPath "$PSScriptRoot/install_receipt.json" -Raw | ConvertFrom-Json
if(!$receipt.complete){throw 'Incomplete save receipt'}
& "$PSScriptRoot/run.ps1" -Manifest 'manifest.json' -Label 'saved'
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --threads 1 --python "$PSScriptRoot/depths.py" -- saved *> "$PSScriptRoot/depths_saved.log"
if($LASTEXITCODE -ne 0){throw 'Native contact sampling failed'}
& py -3.11 "$PSScriptRoot/audit.py" saved
if($LASTEXITCODE -ne 0){throw 'Native return continuity read failed'}
@{complete=$true;asset_save=$true;native_pose_capture=$true;pie_started=$false;gui_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/finish_receipt.json"
