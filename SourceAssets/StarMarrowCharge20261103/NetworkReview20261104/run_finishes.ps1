$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while(-not $taskHeld){
        try{$taskHeld=$taskGate.WaitOne(10000)}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
        if(-not $taskHeld){continue}
        $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and ($_.CommandLine -like '*FPSGAME.uproject*' -or [string]::IsNullOrWhiteSpace($_.CommandLine))) -or
            $_.Name -in @('UnrealBuildTool.exe','cl.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*')
        })
        if($taskBusy.Count){$taskGate.ReleaseMutex();$taskHeld=$false;Start-Sleep -Seconds 10}
    }
    $taskLog="$PSScriptRoot/network-audit-$taskStamp.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=SwordBladeFinishAudit -Shared "-Output=$PSScriptRoot/network-audit.json" -unattended -nop4 -nosplash -nosound -nullrhi -Multiprocess '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' "-abslog=$taskLog" *> "$PSScriptRoot/network-audit-$taskStamp.console.log"
    $taskExit=$LASTEXITCODE
    $taskReport=Get-Content -LiteralPath "$PSScriptRoot/network-audit.json" -Raw | ConvertFrom-Json
    $taskText=Get-Content -LiteralPath $taskLog -Raw
    $taskCompleted=$taskReport.failures -eq 0 -and $taskText -match 'SHARED_FINISH_AUDIT cases=\d+ checks=\d+ failures=0'
    @{exit_code=$taskExit;completed=$taskCompleted;log=$taskLog;actual_network_transport=$false;visual_rendering=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/network-audit-process.json" -Encoding utf8
    if(-not $taskCompleted){throw "Blade finish audit failed; read $taskLog"}
    Write-Output "BLADE_FINISH_AUDIT_COMPLETE $($taskReport.cases) cases $($taskReport.checks) checks"
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
