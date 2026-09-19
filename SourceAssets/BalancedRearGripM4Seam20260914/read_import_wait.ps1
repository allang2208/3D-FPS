param([int]$ImportProcessId)
$taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$ImportProcessId"
if (-not $taskProcess -or $taskProcess.CommandLine -notlike '*BalancedRearGripM4Seam20260914*import_bridge.py*') { throw 'This helper only reads this task import process.' }
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class SeamImportWait {
 [DllImport("advapi32.dll",SetLastError=true)] public static extern IntPtr OpenThreadWaitChainSession(uint flags,IntPtr callback);
 [DllImport("advapi32.dll",SetLastError=true)] public static extern bool GetThreadWaitChain(IntPtr session,IntPtr context,uint flags,uint thread,ref uint count,IntPtr nodes,out bool cycle);
 [DllImport("advapi32.dll")] public static extern void CloseThreadWaitChainSession(IntPtr session);
}
'@
$session = [SeamImportWait]::OpenThreadWaitChainSession(0,[IntPtr]::Zero)
$buffer = [Runtime.InteropServices.Marshal]::AllocHGlobal(280*16)
try {
 $taskThread = (Get-Process -Id $ImportProcessId).Threads | Sort-Object StartTime | Select-Object -First 1
 [uint32]$count=16;[bool]$cycle=$false
 $ok=[SeamImportWait]::GetThreadWaitChain($session,[IntPtr]::Zero,7,$taskThread.Id,[ref]$count,$buffer,[ref]$cycle)
 if (-not $ok) { throw ('Wait chain unavailable: '+[Runtime.InteropServices.Marshal]::GetLastWin32Error()) }
 for ($index=0;$index -lt $count;$index++) {
   $node=[IntPtr]::Add($buffer,280*$index);$kind=[Runtime.InteropServices.Marshal]::ReadInt32($node,0);$state=[Runtime.InteropServices.Marshal]::ReadInt32($node,4)
   if ($kind -eq 8) { [PSCustomObject]@{Kind=$kind;State=$state;ProcessId=[Runtime.InteropServices.Marshal]::ReadInt32($node,8);ThreadId=[Runtime.InteropServices.Marshal]::ReadInt32($node,12)} | ConvertTo-Json -Compress }
   else { [PSCustomObject]@{Kind=$kind;State=$state;Name=[Runtime.InteropServices.Marshal]::PtrToStringUni([IntPtr]::Add($node,8))} | ConvertTo-Json -Compress }
 }
} finally {
 [Runtime.InteropServices.Marshal]::FreeHGlobal($buffer)
 [SeamImportWait]::CloseThreadWaitChainSession($session)
}
