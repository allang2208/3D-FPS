param([string]$ProjectRoot='D:/FPS3D/FPSGAME', [string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$taskProject=Join-Path $ProjectRoot 'FPSGAME.uproject'
$taskScript=Join-Path $PSScriptRoot 'prepare_hand_corpse.py'
$taskReceiptPath=Join-Path $PSScriptRoot 'Receipts/delivery.json'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskLocked=$false
try {
    try { $taskLocked=$taskMutex.WaitOne([TimeSpan]::FromMinutes(30)) }
    catch [Threading.AbandonedMutexException] { $taskLocked=$true }
    if(-not $taskLocked){throw 'Existing UE production batch did not release its mutex.'}
    $taskDeadline=[DateTime]::UtcNow.AddMinutes(30)
    while($true){
        $taskProcesses=@(Get-CimInstance Win32_Process)
        $taskEditors=@($taskProcesses|Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and
            ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME\.uproject')})
        if(@($taskEditors|Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count -gt 0){
            throw 'FPSGAME editor is running. Loaded packages were preserved; no process was stopped.'
        }
        $taskBuilds=@($taskProcesses|Where-Object {$_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if($taskEditors.Count -eq 0 -and $taskBuilds.Count -eq 0){break}
        if([DateTime]::UtcNow -ge $taskDeadline){throw 'Existing UE build/commandlet did not release. No process was stopped.'}
        Start-Sleep -Seconds 5
    }
    $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $taskLog=Join-Path $ProjectRoot ("Saved/Logs/MonsterRagdollStandard-Hand-$taskStamp.log")
    $taskArgs='"'+$taskProject+'" -run=pythonscript -script="'+$taskScript+'" -unattended -nop4 -nosplash -nosound -nullrhi -multiprocess -DDC=InstalledNoZenLocalFallback -abslog="'+$taskLog+'"'
    $taskProcess=Start-Process -FilePath (Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') -ArgumentList $taskArgs -WindowStyle Hidden -PassThru
    Write-Output "Hand asset production PID=$($taskProcess.Id) Log=$taskLog"
    $taskProcess.WaitForExit()
    if($taskProcess.ExitCode -ne 0){throw "Hand asset production exited $($taskProcess.ExitCode); log $taskLog"}
    $taskSavedPath=Join-Path $PSScriptRoot 'Receipts/hand-physics-saved.json'
    if(-not(Test-Path -LiteralPath $taskSavedPath)){throw "Hand production ended without a saved-asset receipt; log $taskLog"}
    $taskReceipt=Get-Content -LiteralPath $taskReceiptPath -Raw|ConvertFrom-Json -AsHashtable
    $taskReceipt['hand_asset']='Saved'
    $taskReceipt['hand_production_log']=$taskLog
    $taskReceipt['hand_saved_receipt']=$taskSavedPath
    $taskReceipt['hand_asset_path']='/Game/Monsters/FleshHand/PA_FleshHand_Corpse'
    if($taskReceipt.targets['FPSGAME Win64 Development'] -eq 'Succeeded' -and $taskReceipt.targets['FPSGAMEEditor Win64 Development'] -eq 'Succeeded'){
        $taskReceipt['status']='OrdinaryBuildsCompletedHandPhysicsSaved'
    }
    $taskReceipt['production_completed_utc']=[DateTime]::UtcNow.ToString('o')
    $taskReceipt|ConvertTo-Json -Depth 12|Set-Content -LiteralPath $taskReceiptPath -Encoding utf8
    Write-Output 'Hand corpse physics saved. No editor/game was launched and runtime remains untested.'
} finally {
    if($taskLocked){$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
