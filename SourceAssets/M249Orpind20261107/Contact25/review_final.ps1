$ErrorActionPreference='Stop'
$root=$PSScriptRoot
& "$root/run.ps1" -Manifest manifest.json -Label verified
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --threads 2 --python "$root/depths.py" -- verified *> "$root/depths_verified.log"
if($LASTEXITCODE){throw 'Native geometry review failed'}
& py -3.11 "$root/audit.py" verified *> "$root/audit_verified.log"
& py -3.11 "$root/sheets.py" verified *> "$root/sheets_verified.log"
& py -3.11 "$root/video.py" verified *> "$root/video_verified.log"
Write-Output 'CONTACT25_FINAL_NATIVE_COMPLETE'
