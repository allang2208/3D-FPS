$ErrorActionPreference='Stop'
$root=$PSScriptRoot
& py -3.11 "$root/apply_final_clearance.py"
if($LASTEXITCODE){throw 'Clearance authoring failed'}
& py -3.11 "$root/publish_profiles.py" *> "$root/publish_clearance.log"
if($LASTEXITCODE){throw 'Profile authoring failed'}
& "$root/assets.ps1" -Script install.py
& "$root/run.ps1" -Manifest final_clearance_manifest.json -Label polished
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --threads 2 --python "$root/depths.py" -- polished *> "$root/depths_polished.log"
if($LASTEXITCODE){throw 'Native contact review failed'}
& py -3.11 "$root/audit.py" verified polished *> "$root/audit_final.log"
Write-Output 'CONTACT25_FINAL_CLEARANCE_SAVED_AND_READ_BACK'
