param()
$ErrorActionPreference='Stop'
$reviewProject='D:/FPS3D/FPSGAME'
$reviewScript=Join-Path $PSScriptRoot 'read_saved_assets.py'
$reviewStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$reviewGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$reviewHeld=$false
$reviewDeadline=[DateTime]::UtcNow.AddMinutes(15)
try {
    while(-not $reviewHeld) {
        if([DateTime]::UtcNow -gt $reviewDeadline){throw 'Asset readback is still waiting for the UE batch.'}
        try{$reviewHeld=$reviewGate.WaitOne(10000)}catch [Threading.AbandonedMutexException]{$reviewHeld=$true}
        if(-not $reviewHeld){continue}
        $reviewProcesses=@(Get-CimInstance Win32_Process)
        $reviewBusy=@($reviewProcesses | Where-Object {
            $_.Name -in @('cl.exe','link.exe','UnrealBuildTool.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME')
        })
        if($reviewBusy.Count){$reviewGate.ReleaseMutex();$reviewHeld=$false;Start-Sleep -Seconds 10}
    }
    $reviewEditors=@($reviewProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and ($_.CommandLine -match 'FPSGAME' -or [string]::IsNullOrWhiteSpace($_.CommandLine))})
    if($reviewEditors.Count) {
        $reviewGate.ReleaseMutex();$reviewHeld=$false
        & "$reviewProject/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $reviewScript -OutputFile "$PSScriptRoot/readback-$reviewStamp-response.txt" -MaxOutputChars 2000 -QueueWaitSeconds 300 -RequestTimeoutSeconds 240
        if($LASTEXITCODE -ne 0){throw 'Existing-editor asset readback did not complete.'}
    } else {
        $reviewLog=Join-Path $PSScriptRoot "readback-$reviewStamp.log"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$reviewProject/FPSGAME.uproject" -run=pythonscript "-script=$reviewScript" -unattended -nop4 -nosplash -nosound -Multiprocess -nullrhi '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' "-abslog=$reviewLog" *> "$reviewLog.console.txt"
        if($LASTEXITCODE -ne 0 -or -not (Select-String -LiteralPath $reviewLog -SimpleMatch 'INVENTORY_ICON_REVIEW_SAVED_ASSETS_OK' -Quiet)){throw "Asset readback failed: $reviewLog"}
        Write-Output 'Independent-process saved asset readback succeeded.'
    }
} finally {if($reviewHeld){$reviewGate.ReleaseMutex()};$reviewGate.Dispose()}
