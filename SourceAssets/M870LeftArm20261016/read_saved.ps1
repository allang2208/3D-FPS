$ErrorActionPreference='Stop'
$projectPattern='D:/FPS3D/FPSGAME/FPSGAME\.uproject(?:["\s]|$)'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
$runtimeGamePattern='(?:^|\s)-game(?:\s|$)'
$deadline=[DateTime]::UtcNow.AddMinutes(15)
try {
    while(-not $held) {
        if([DateTime]::UtcNow -gt $deadline){throw 'The existing build or asset batch has not finished; no asset import was started.'}
        $processes=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='cl.exe' OR Name='link.exe'")
        $liveEditor=@($processes | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch $runtimeGamePattern -and ($_.CommandLine -replace '\\','/') -match $projectPattern})
        # Existing editor imports use its already loaded module and bridge gate.
        # Only a new commandlet must wait for binaries to finish building.
        $busy=@($processes | Where-Object {($liveEditor.Count -eq 0 -and (($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'cl.exe' -or $_.Name -eq 'link.exe')) -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -notmatch $runtimeGamePattern -and ($_.CommandLine -replace '\\','/') -match $projectPattern)})
        if($busy.Count -gt 0){Start-Sleep -Seconds 5;continue}
        try {$held=$gate.WaitOne(1000)} catch [Threading.AbandonedMutexException] {$held=$true}
    }
    $editor=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -notmatch $runtimeGamePattern -and ($_.CommandLine -replace '\\','/') -match $projectPattern}
    $started=[DateTime]::UtcNow
    if($editor) {
        & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript 'D:/FPS3D/FPSGAME/SourceAssets/M870LeftArm20261016/read_saved.py' -QueueWaitSeconds 600 -RequestTimeoutSeconds 600 -OutputFile ('D:/FPS3D/FPSGAME/SourceAssets/M870LeftArm20261016/readback_bridge_'+[guid]::NewGuid().ToString('N')+'.txt') -MaxOutputChars 2000
    } else {
        # Standalone -game processes have no editor asset-save service. Keep
        # excluding editors and authoring commandlets while holding the same gate.
        $owners=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
            $_.CommandLine -notmatch $runtimeGamePattern -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or ($_.CommandLine -replace '\\','/') -match $projectPattern)
        })
        if($owners.Count -gt 0){throw 'An editor or asset commandlet appeared; preserve its asset ownership.'}
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' `
            -run=pythonscript '-script=D:/FPS3D/FPSGAME/SourceAssets/M870LeftArm20261016/read_saved.py' `
            -unattended -nop4 -nosplash -nosound -AllowCommandletRendering -RenderOffscreen `
            '-abslog=D:/FPS3D/FPSGAME/SourceAssets/M870LeftArm20261016/read_saved.log'
        if($LASTEXITCODE -ne 0){throw "M870 saved-asset readback failed ($LASTEXITCODE); see read_saved.log."}
    }
    $receiptPath=Join-Path $PSScriptRoot 'saved_assets.json'
    if(-not (Test-Path -LiteralPath $receiptPath) -or (Get-Item -LiteralPath $receiptPath).LastWriteTimeUtc -lt $started){throw 'M870 readback produced no current receipt.'}
    $receipt=Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if(-not $receipt.completed){throw ('M870 left arm was not saved. '+$receipt.deferred_reason)}
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
