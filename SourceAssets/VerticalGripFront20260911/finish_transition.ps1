$ErrorActionPreference='Stop'
$gripBlender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
foreach($gripVariant in @('vertical','prism')){
    & $gripBlender -b -t 5 --python-exit-code 1 --python "$PSScriptRoot/check_geometry.py" -- akm $gripVariant *> "$PSScriptRoot/geometry-akm-$gripVariant-final.log"
    if($LASTEXITCODE){throw 'Geometry failed'}
    & $gripBlender -b -t 5 --python-exit-code 1 --python "$PSScriptRoot/check_thumb_gun.py" -- akm $gripVariant *> "$PSScriptRoot/thumb-gun-akm-$gripVariant-final.log"
    if($LASTEXITCODE){throw 'Thumb gun failed'}
}
& $gripBlender -b -t 5 --python-exit-code 1 --python "$PSScriptRoot/compare_source_self.py" *> "$PSScriptRoot/self-source-final.log"
if($LASTEXITCODE){throw 'Source contacts failed'}
& $gripBlender -b -t 5 --python-exit-code 1 --python "$PSScriptRoot/assemble_editable.py" *> "$PSScriptRoot/editable.log"
if($LASTEXITCODE){throw 'Editable assembly failed'}
Write-Output 'FRONT_TRANSITION_GEOMETRY_PASS'
