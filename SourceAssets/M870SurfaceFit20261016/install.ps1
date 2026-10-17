$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
$deadline=[DateTime]::UtcNow.AddMinutes(15)
try {
    while(-not $held) {
        if([DateTime]::UtcNow -gt $deadline){throw 'The existing build or asset batch has not finished; no asset import was started.'}
        $busy=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'cl.exe' -or $_.Name -eq 'link.exe' -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME.uproject')})
        if($busy.Count -gt 0){Start-Sleep -Seconds 5;continue}
        try {$held=$gate.WaitOne(1000)} catch [Threading.AbandonedMutexException] {$held=$true}
    }
    $editor=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'}
    if($editor) {
        & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript 'D:/FPS3D/FPSGAME/SourceAssets/M870SurfaceFit20261016/install_animations.py' -QueueWaitSeconds 600 -RequestTimeoutSeconds 600 -OutputFile ('D:/FPS3D/FPSGAME/SourceAssets/M870SurfaceFit20261016/install_bridge_'+[guid]::NewGuid().ToString('N')+'.txt') -MaxOutputChars 2000
    } else {
        & 'D:/FPS3D/FPSGAME/Tools/ModularOutfit/Run-Authoring.ps1' -Script 'SourceAssets/M870SurfaceFit20261016/install_animations.py' -Log 'SourceAssets/M870SurfaceFit20261016/install_animations.log'
    }
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
