$ErrorActionPreference='Stop'
$priorBuild=Get-Process -Id 98016 -ErrorAction SilentlyContinue
if($priorBuild){
    Write-Output 'Waiting for existing build 98016 to finish naturally'
    Wait-Process -InputObject $priorBuild -Timeout 1200
}
& "$PSScriptRoot/build.ps1"
