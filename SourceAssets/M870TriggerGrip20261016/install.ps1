$ErrorActionPreference='Stop'
$projectPattern='D:/FPS3D/FPSGAME/FPSGAME\.uproject(?:["\s]|$)'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
$deadline=[DateTime]::UtcNow.AddMinutes(15)
try {
    while(-not $held) {
        if([DateTime]::UtcNow -gt $deadline){throw 'The existing build or asset batch has not finished; no asset import was started.'}
        $processes=@(Get-CimInstance Win32_Process)
        $liveEditor=@($processes | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and ($_.CommandLine -replace '\\','/') -match $projectPattern})
        # Existing editor imports use its already loaded module and bridge gate.
        # Only a new commandlet must wait for binaries to finish building.
        $busy=@($processes | Where-Object {($liveEditor.Count -eq 0 -and (($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'cl.exe' -or $_.Name -eq 'link.exe')) -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and ($_.CommandLine -replace '\\','/') -match $projectPattern)})
        if($busy.Count -gt 0){Start-Sleep -Seconds 5;continue}
        try {$held=$gate.WaitOne(1000)} catch [Threading.AbandonedMutexException] {$held=$true}
    }
    $editor=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {($_.CommandLine -replace '\\','/') -match $projectPattern}
    $started=[DateTime]::UtcNow
    if($editor) {
        & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript 'D:/FPS3D/FPSGAME/SourceAssets/M870TriggerGrip20261016/install_animations.py' -QueueWaitSeconds 600 -RequestTimeoutSeconds 600 -OutputFile ('D:/FPS3D/FPSGAME/SourceAssets/M870TriggerGrip20261016/install_bridge_'+[guid]::NewGuid().ToString('N')+'.txt') -MaxOutputChars 2000
    } else {
        & 'D:/FPS3D/FPSGAME/Tools/ModularOutfit/Run-Authoring.ps1' -Script 'SourceAssets/M870TriggerGrip20261016/install_animations.py' -Log 'SourceAssets/M870TriggerGrip20261016/install_animations.log'
    }
    $receiptPath=Join-Path $PSScriptRoot 'install_receipt.json'
    if(-not (Test-Path -LiteralPath $receiptPath) -or (Get-Item -LiteralPath $receiptPath).LastWriteTimeUtc -lt $started){throw 'M870 import produced no current save receipt.'}
    $receipt=Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if(-not $receipt.completed){throw ('M870 trigger grip was not saved. '+$receipt.deferred_reason)}
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
