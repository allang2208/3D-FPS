$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskEngine='E:/Program Files (x86)/UE_5.8'
$taskStamp=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')
$taskReceiptPath=Join-Path $PSScriptRoot 'delivery.json'
$taskReceipt=[ordered]@{state='waiting';targets=@{};logs=@{};bite_trigger_cm=450;mouth_reach_cm=150;vertical_slack_cm=52.5;runtime_tested=$false}
function Save-Receipt {
    [IO.File]::WriteAllText($taskReceiptPath,($taskReceipt|ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
}
function Wait-BuildWindow {
    $taskDeadline=[DateTime]::UtcNow.AddMinutes(40)
    while($true){
        $taskProcesses=@(Get-CimInstance Win32_Process)
        if(@($taskProcesses|Where-Object {$_.Name -eq 'UnrealEditor.exe' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME\.uproject')}).Count){
            throw 'FPSGAME editor is running; its loaded content is preserved.'
        }
        $taskBusy=@($taskProcesses|Where-Object {$_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe','UnrealEditor-Cmd.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if(!$taskBusy.Count){return}
        if([DateTime]::UtcNow -gt $taskDeadline){throw 'Existing build did not release; no process was stopped.'}
        Start-Sleep -Seconds 5
    }
}
try {
    Save-Receipt
    foreach($taskTarget in @('FPSGAMEEditor','FPSGAME')){
        $taskReceipt.state='waiting_for_'+$taskTarget;Save-Receipt;Wait-BuildWindow
        $taskLog=Join-Path $PSScriptRoot ('build-'+$taskTarget+'-'+$taskStamp+'.log')
        $taskReceipt.state='building_'+$taskTarget;$taskReceipt.logs[$taskTarget]=$taskLog;Save-Receipt
        & (Join-Path $taskEngine 'Engine/Build/BatchFiles/Build.bat') $taskTarget Win64 Development "-Project=$taskProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE "-Log=$taskLog"
        if($LASTEXITCODE -ne 0){throw "$taskTarget build failed: $LASTEXITCODE"}
        $taskReceipt.targets[$taskTarget]='Succeeded';Save-Receipt
    }
    $taskReceipt.state='builds_completed';Save-Receipt
} catch {$taskReceipt.state='blocked_or_failed';$taskReceipt['error']=$_.Exception.Message;Save-Receipt;throw}
