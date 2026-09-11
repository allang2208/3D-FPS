$ErrorActionPreference='Stop'
foreach($gripCase in @(@('m4','canted'),@('akm','canted'),@('akm','vertical'),@('akm','prism'),@('akm','angled'))){
    & "$PSScriptRoot/run.ps1" -Weapon $gripCase[0] -Grip $gripCase[1] -Run ($gripCase[0]+'-'+$gripCase[1]+'-accepted')
}
foreach($gripName in @('canted','vertical')){
    & "$PSScriptRoot/run.ps1" -Weapon akm -Grip $gripName -Run ('akm-'+$gripName+'-ui-accepted') -UI
}
Write-Output 'GRIP_ALL_RUNTIME_ACCEPTED'
