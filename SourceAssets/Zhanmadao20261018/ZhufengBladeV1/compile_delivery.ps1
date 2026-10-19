param([string]$Attempt='zhufeng-02')
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
function Get-TaskBuildOccupancy {
    $active=Get-Process UnrealEditor,UnrealEditor-Cmd,UnrealBuildTool,FPSGAME -ErrorAction SilentlyContinue
    $ubt=Get-CimInstance Win32_Process -Filter "Name = 'dotnet.exe'" | Where-Object { $_.CommandLine -like '*UnrealBuildTool.dll*' }
    return ($active -or $ubt)
}
function Write-TaskBuildState([string]$phase,[string]$message='') {
    @{phase=$phase;message=$message;time=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/compile-state.json" -Encoding UTF8
}
try {
    foreach($taskTarget in @('FPSGAMEEditor','FPSGAME')) {
        Write-TaskBuildState 'queued' $taskTarget
        $taskDeadline=(Get-Date).AddMinutes(30)
        while(-not $taskHeld) {
            if((Get-Date) -gt $taskDeadline){throw 'Existing UE/build occupancy did not clear; preserved it.'}
            if(Get-TaskBuildOccupancy){Start-Sleep -Seconds 10;continue}
            try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))}
            catch [Threading.AbandonedMutexException] {$taskHeld=$true}
            if($taskHeld -and (Get-TaskBuildOccupancy)){$taskGate.ReleaseMutex();$taskHeld=$false}
        }
        Write-TaskBuildState 'building' $taskTarget
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -NoUBA -NoUBTMakefiles -MaxParallelActions=6 "-Log=$taskRoot/build-$taskTarget-$Attempt.log" *> "$taskRoot/build-$taskTarget-console-$Attempt.log"
        $taskExit=$LASTEXITCODE
        @{target=$taskTarget;exit_code=$taskExit;finished=(Get-Date).ToString('o');game_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/build-$taskTarget-receipt-$Attempt.json" -Encoding UTF8
        $taskGate.ReleaseMutex();$taskHeld=$false
        if($taskExit -ne 0){throw "$taskTarget build failed ($taskExit)"}
    }
    & py -3.11 -X utf8 "$taskRoot/finalize_delivery.py"
    if($LASTEXITCODE -ne 0){throw 'Recording delivery failed'}
    Write-TaskBuildState 'complete'
} catch {Write-TaskBuildState 'failed' $_.Exception.Message;throw}
finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
