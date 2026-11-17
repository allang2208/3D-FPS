param([string]$Suffix='02')
$ErrorActionPreference='Stop'
$mbGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$mbHeld=$false
try{
 Write-Output 'Waiting for one serial map-marker test batch.'
 while(-not $mbHeld){try{$mbHeld=$mbGate.WaitOne(50000)}catch [Threading.AbandonedMutexException]{$mbHeld=$true}}
 # Reentrant acquisition in the individual launchers keeps this batch serialized with other UE work.
 & "$PSScriptRoot/run_network_check.ps1" -Run "normal-$Suffix" -Lag 0 -Loss 0 -Port 19938
 & "$PSScriptRoot/run_network_check.ps1" -Run "weak-$Suffix" -Lag 60 -Loss 2 -Port 19939
 & "$PSScriptRoot/run_lifecycle_check.ps1" -Run "lifecycle-$Suffix" -Runtime "D:/FPS3D/FPSGAME/Saved/MapMarkerSharing20261115/weak-$Suffix/Runtime"
}finally{if($mbHeld){$mbGate.ReleaseMutex()};$mbGate.Dispose()}
