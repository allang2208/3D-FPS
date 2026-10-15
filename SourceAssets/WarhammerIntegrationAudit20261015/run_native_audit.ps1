$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    $started=[DateTime]::UtcNow
    while(-not $held -and ([DateTime]::UtcNow-$started).TotalMinutes -lt 10) {
        try { $held=$gate.WaitOne(1000) } catch [Threading.AbandonedMutexException] {$held=$true}
    }
    if(-not $held){throw 'Existing asset batch did not release its gate.'}
    while(@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'UnrealBuildTool.*FPSGAMEEditor'}).Count -gt 0){Start-Sleep -Seconds 3}
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' -run=WarhammerModificationAudit "-Out=$taskRoot\native_report.json" -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess "-abslog=$taskRoot\native-audit.log" *> "$taskRoot\native-audit-console.log"
    $taskCode=$LASTEXITCODE
    @{exit_code=$taskCode;finished=(Get-Date).ToString('s');real_network_transport_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot\native-audit-receipt.json" -Encoding UTF8
    Get-Content -LiteralPath "$taskRoot\native-audit-console.log" -Tail 8
    exit $taskCode
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
