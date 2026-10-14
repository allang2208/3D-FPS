$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskScript=Join-Path $taskProject 'Tools/MonsterAI/migrate_aps_navigation.py'
$taskOutput=Join-Path $taskProject 'Saved/APSNavigationMigration'
[IO.Directory]::CreateDirectory($taskOutput)|Out-Null
$taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskDeadline=[DateTime]::UtcNow.AddMinutes(30)
try {
    while(-not $taskHeld){
        if([DateTime]::UtcNow -gt $taskDeadline){throw 'Production window remained occupied; no other process was stopped.'}
        if(@(Get-CimInstance Win32_Process|Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count){throw 'An open editor holds the maps; close it and rerun. No process was stopped.'}
        try{$taskHeld=$taskGate.WaitOne(1000)}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
        # Join the shared queue before waiting for a pre-existing build/window.
        # Otherwise consecutive producers can repeatedly occupy the idle gap.
        while($taskHeld){
            $taskProcesses=@(Get-CimInstance Win32_Process)
            if(@($taskProcesses|Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count){
                $taskGate.ReleaseMutex();$taskHeld=$false;break
            }
            # Game-target builds do not replace loaded editor modules. Only
            # editor builds and other commandlets occupy this asset window.
            $taskBusy=@($taskProcesses|Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe' -or ($_.Name -in @('UnrealBuildTool.exe','dotnet.exe') -and $_.CommandLine -match 'UnrealBuildTool' -and $_.CommandLine -match 'FPSGAMEEditor')})
            if(-not $taskBusy.Count){break}
            if([DateTime]::UtcNow -gt $taskDeadline){throw 'Production window remained occupied; no other process was stopped.'}
            Start-Sleep -Seconds 5
        }
    }
    if($taskHeld){
        if(@(Get-CimInstance Win32_Process|Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe')}).Count){throw 'An editor started before migration; no asset changed.'}
        $taskLog=Join-Path $taskOutput "migration-$taskStamp.log"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$taskScript" -unattended -nop4 -nosound -NullRHI -NoSplash "-abslog=$taskLog" *> (Join-Path $taskOutput "console-$taskStamp.log")
        if($LASTEXITCODE -ne 0){throw "Migration failed; see $taskLog"}
    }
    $taskReceipt=Get-Content (Join-Path $taskOutput 'migration.json') -Raw|ConvertFrom-Json
    if(-not $taskReceipt.complete){throw 'Migration has not completed; preserve its receipt.'}
    Write-Output "APS navigation data migrated and maps saved."
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
