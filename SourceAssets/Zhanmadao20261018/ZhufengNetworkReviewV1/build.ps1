param([string]$Attempt='01',[string[]]$Targets=@('FPSGAMEEditor','FPSGAME'))
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
function Write-TaskPhase([string]$phase,[string]$target) {
    @{phase=$phase;target=$target;updated=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/build-state.json" -Encoding UTF8
}
function Test-TaskBusy {
    $editors=Get-Process UnrealEditor,UnrealEditor-Cmd,UnrealBuildTool,FPSGAME -ErrorAction SilentlyContinue
    $builds=Get-CimInstance Win32_Process -Filter "Name = 'dotnet.exe'" | Where-Object {$_.CommandLine -like '*UnrealBuildTool.dll*'}
    return ($editors -or $builds)
}
try {
    foreach($taskTarget in $Targets) {
        Write-TaskPhase 'queued' $taskTarget
        $taskDeadline=(Get-Date).AddMinutes(20)
        while(-not $taskHeld) {
            if((Get-Date) -gt $taskDeadline){throw 'UE/build occupancy did not clear; preserved running work.'}
            if(Get-Process UnrealEditor,FPSGAME -ErrorAction SilentlyContinue){Start-Sleep -Seconds 10;continue}
            try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))}
            catch [Threading.AbandonedMutexException] {$taskHeld=$true}
            # Queue on the shared gate between asset batches, then wait only
            # for already-running background UE/UBT work to finish.
            while($taskHeld -and (Test-TaskBusy)) {
                if(Get-Process UnrealEditor,FPSGAME -ErrorAction SilentlyContinue){$taskGate.ReleaseMutex();$taskHeld=$false;break}
                if((Get-Date) -gt $taskDeadline){throw 'Background UE/build occupancy did not clear; preserved it.'}
                Start-Sleep -Seconds 5
            }
        }
        Write-TaskPhase 'building' $taskTarget
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=3 "-Log=$taskRoot/build-$taskTarget-$Attempt.log" *> "$taskRoot/build-$taskTarget-console-$Attempt.txt"
        $taskExit=$LASTEXITCODE
        @{target=$taskTarget;exit_code=$taskExit;finished=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/build-$taskTarget-$Attempt-receipt.json" -Encoding UTF8
        if($taskExit -eq 0 -and $taskTarget -eq 'FPSGAMEEditor') {
            Write-TaskPhase 'isolated-authority-checks' 'ZhufengOnly'
            $taskAuditStart=Get-Date
            & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=SkillNetworkAudit -ZhufengOnly -unattended -nosplash -NullRHI -NoSound -NoP4 -UTF8Output "-abslog=$taskRoot/audit-$Attempt.log" *> "$taskRoot/audit-console-$Attempt.txt"
            $taskAuditExit=$LASTEXITCODE
            @{exit_code=$taskAuditExit;finished=(Get-Date).ToString('o');real_network_transport_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/audit-$Attempt-receipt.json" -Encoding UTF8
            $taskAuditResult='D:/FPS3D/FPSGAME/Saved/ZhufengNetworkReview20261019/authority-result.json'
            if((Test-Path -LiteralPath $taskAuditResult) -and (Get-Item -LiteralPath $taskAuditResult).LastWriteTime -ge $taskAuditStart) {
                Copy-Item -LiteralPath $taskAuditResult -Destination "$taskRoot/authority-result-$Attempt.json"
            } else {throw 'No fresh authority check result was produced'}
            if($taskAuditExit -ne 0){throw "Zhufeng isolated authority checks failed ($taskAuditExit)"}
        }
        $taskGate.ReleaseMutex();$taskHeld=$false
        if($taskExit -ne 0){throw "$taskTarget build failed ($taskExit)"}
    }
    & py -3.11 -X utf8 "$taskRoot/finalize.py"
    if($LASTEXITCODE -ne 0){throw 'Delivery receipt write failed'}
    Write-TaskPhase 'complete' 'Editor and Game'
} catch {Write-TaskPhase 'failed' $_.Exception.Message;throw}
finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
