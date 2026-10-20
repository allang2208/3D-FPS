$ErrorActionPreference='Stop'
# The user closed the interactive editor. This already-running commandlet
# still owns project modules; wait for its natural exit, without signalling it.
if(Get-Process -Id 64012 -ErrorAction SilentlyContinue){Wait-Process -Id 64012 -Timeout 1200}
& "$PSScriptRoot/run_finish.ps1"
