$ErrorActionPreference='Stop'
# Observed UBT process from this task's start. Wait for its natural completion
# before joining the shared UE gate; never send coordination messages or kill it.
$priorBuild=Get-Process -Id 91600 -ErrorAction SilentlyContinue
if($priorBuild){
    Write-Output 'Waiting for the existing native build to finish'
    Wait-Process -InputObject $priorBuild -Timeout 1200
}
& "$PSScriptRoot/build.ps1"
