$ErrorActionPreference='Stop'
$jobs=@(Get-Content -LiteralPath "$PSScriptRoot/settle_processes.json" -Raw | ConvertFrom-Json)
do {
 $active=@($jobs | Where-Object { Get-Process -Id $_.pid -ErrorAction SilentlyContinue })
 if($active.Count){Start-Sleep -Seconds 5}
} while($active.Count)
foreach($job in $jobs){
 if(!(Select-String -LiteralPath "$PSScriptRoot/$($job.family).settle.log" -SimpleMatch 'NATIVE_SETTLE_COMPLETE' -Quiet)){throw "Incomplete source-frame correction: $($job.family)"}
}
& py -3.11 "$PSScriptRoot/publish_native.py"
if($LASTEXITCODE -ne 0){throw 'Native profile authoring failed'}
& "$PSScriptRoot/assets.ps1" -Script 'install.py'
$receipt=Get-Content -LiteralPath "$PSScriptRoot/install_receipt.json" -Raw | ConvertFrom-Json
if(!$receipt.complete){throw 'Incomplete save receipt'}
& "$PSScriptRoot/run.ps1" -Manifest 'manifest.json' -Label 'polished'
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --threads 1 --python "$PSScriptRoot/depths.py" -- polished *> "$PSScriptRoot/depths_polished.log"
if($LASTEXITCODE -ne 0){throw 'Native contact sampling failed'}
& py -3.11 "$PSScriptRoot/audit.py" polished
if($LASTEXITCODE -ne 0){throw 'Native return continuity read failed'}
& py -3.11 "$PSScriptRoot/video.py" polished
if($LASTEXITCODE -ne 0){throw 'Native preview assembly failed'}
@{complete=$true;asset_save=$true;native_pose_capture=$true;pie_started=$false;gui_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/final_receipt.json"
