param([int]$BatchPid)
$ErrorActionPreference='Stop'
$batch=Get-CimInstance Win32_Process -Filter ('ProcessId='+$BatchPid)
if($batch.Name -ne 'UnrealEditor-Cmd.exe' -or $batch.CommandLine -notlike '*\HeroHandV4\full_install.py*') {throw 'Only this revision import process may be inspected.'}
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class HeroHandWaitChain {
    [DllImport("advapi32.dll", SetLastError=true)] public static extern IntPtr OpenThreadWaitChainSession(uint flags, IntPtr callback);
    [DllImport("advapi32.dll", SetLastError=true)] public static extern bool GetThreadWaitChain(IntPtr session,IntPtr context,uint flags,uint tid,ref uint count,IntPtr nodes,out bool cycle);
    [DllImport("advapi32.dll")] public static extern void CloseThreadWaitChainSession(IntPtr session);
}
'@
$handle=[HeroHandWaitChain]::OpenThreadWaitChainSession(0,[IntPtr]::Zero)
$nodes=[Runtime.InteropServices.Marshal]::AllocHGlobal(16*280)
try {
    $main=(Get-Process -Id $BatchPid).Threads | Select-Object -First 1
    [uint32]$count=16; $cycle=$false
    if(-not [HeroHandWaitChain]::GetThreadWaitChain($handle,[IntPtr]::Zero,0,$main.Id,[ref]$count,$nodes,[ref]$cycle)) {
        throw ('Wait chain unavailable: '+[Runtime.InteropServices.Marshal]::GetLastWin32Error())
    }
    Write-Output ('Wait chain cycle: '+$cycle)
    for($i=0;$i -lt $count;$i++) {
        $node=[IntPtr]::Add($nodes,280*$i)
        $kind=[Runtime.InteropServices.Marshal]::ReadInt32($node,0)
        $status=[Runtime.InteropServices.Marshal]::ReadInt32($node,4)
        if($kind -eq 8) {
            [pscustomobject]@{Kind=$kind; Status=$status; Process=[Runtime.InteropServices.Marshal]::ReadInt32($node,8); Thread=[Runtime.InteropServices.Marshal]::ReadInt32($node,12)}
        } else {
            [pscustomobject]@{Kind=$kind; Status=$status; Object=[Runtime.InteropServices.Marshal]::PtrToStringUni([IntPtr]::Add($node,8))}
        }
    }
} finally {
    [HeroHandWaitChain]::CloseThreadWaitChainSession($handle)
    [Runtime.InteropServices.Marshal]::FreeHGlobal($nodes)
}
