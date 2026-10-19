param([Parameter(Mandatory=$true)][string]$Script,[Parameter(Mandatory=$true)][string]$Receipt)
$ErrorActionPreference='Stop';$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try{try{$held=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}; & python D:/FPS3D/FPSGAME/Tools/SteelArmet/bridge_available_port.py $Script *> $Receipt; $result=$LASTEXITCODE;Get-Content $Receipt -Tail 2;exit $result}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
