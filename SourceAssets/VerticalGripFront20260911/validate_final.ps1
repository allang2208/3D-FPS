$ErrorActionPreference='Stop'
$gripBlender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
foreach($gripWeapon in @('m4','akm')){
    foreach($gripVariant in @('vertical','prism')){
        & $gripBlender -b -t 5 --python-exit-code 1 --python "$PSScriptRoot/check_geometry.py" -- $gripWeapon $gripVariant *> "$PSScriptRoot/geometry-$gripWeapon-$gripVariant-final.log"
        if($LASTEXITCODE){throw 'Geometry failed'}
        & $gripBlender -b -t 5 --python-exit-code 1 --python "$PSScriptRoot/check_thumb_gun.py" -- $gripWeapon $gripVariant *> "$PSScriptRoot/thumb-gun-$gripWeapon-$gripVariant-final.log"
        if($LASTEXITCODE){throw 'Thumb gun failed'}
        if($gripWeapon -eq 'm4'){
            & $gripBlender -b -t 5 --python-exit-code 1 --python "$PSScriptRoot/validate_m4.py" -- $gripVariant *> "$PSScriptRoot/source-m4-$gripVariant-final.log"
            if($LASTEXITCODE){throw 'Source validation failed'}
        }
        Write-Output "FRONT_FAMILY_CHECKED $gripWeapon $gripVariant"
    }
}
& $gripBlender -b -t 5 --python-exit-code 1 --python "$PSScriptRoot/compare_source_self.py" *> "$PSScriptRoot/self-source-final.log"
if($LASTEXITCODE){throw 'Source contacts failed'}
