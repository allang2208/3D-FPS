param([Parameter(Mandatory=$true)][string]$Stamp)
$ErrorActionPreference='Stop'
$mageDirectory='D:/FPS3D/FPSGAME/SourceAssets/BlueMageSetAudit20261019/Wire/'+$Stamp
$magePeers=@{};$mageRoles=@{};$mageExits=@{};$mageDeadline=(Get-Date).AddMinutes(8)
while((Get-Date)-lt $mageDeadline){
    $rows=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -like '*-MageOutfitWireAudit*' -and $_.CommandLine -like ('*'+$Stamp+'*')})
    foreach($row in $rows){
        $id=[int]$row.ProcessId
        if(-not $magePeers.ContainsKey($id)){
            $peer=[Diagnostics.Process]::GetProcessById($id);$mageProcessHandle=$peer.Handle;$magePeers[$id]=$peer
            $mageRoles[$id]=if($row.CommandLine -like '*/rejoin.log*'){'rejoin'}elseif($row.CommandLine -like '*/host.log*'){'host'}else{'client'}
        }
    }
    foreach($id in @($magePeers.Keys)){
        $peer=$magePeers[$id]
        if($peer.HasExited -and -not $mageExits.ContainsKey($id)){
            $mageExits[$id]=@{pid=$id;role=$mageRoles[$id];exit_code=$peer.ExitCode}
            @($mageExits.Values) | ConvertTo-Json | Set-Content -LiteralPath ($mageDirectory+'/peer-exits.json') -Encoding utf8
            Write-Output "MAGE_PEER_EXIT $($mageRoles[$id]) PID=$id CODE=$($peer.ExitCode)"
        }
    }
    if($mageExits.Count -ge 3){break};Start-Sleep -Seconds 2
}
foreach($peer in $magePeers.Values){$peer.Dispose()}
if($mageExits.Count -lt 3){throw 'Not all peer exit codes were observed.'}
