$ErrorActionPreference='Stop'
foreach($gripWeapon in @('m4','akm')){
    foreach($gripVariant in @('vertical','prism')){
        & "$PSScriptRoot/run.ps1" -Weapon $gripWeapon -Grip $gripVariant -Run "front-$gripWeapon-$gripVariant-final"
    }
}
Write-Output 'FRONT_RUNTIME_ALL_PASS'
