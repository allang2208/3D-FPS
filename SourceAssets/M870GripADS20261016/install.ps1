$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$deadline=[DateTime]::UtcNow.AddMinutes(12)
try {
    while(-not $taskHeld) {
        $remaining=[Math]::Max(0,[int]($deadline-[DateTime]::UtcNow).TotalMilliseconds)
        if($remaining -eq 0){throw 'An existing engine process still occupies the asset authoring window; no import was sent.'}
        try {$taskHeld=$taskGate.WaitOne($remaining)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
        if(-not $taskHeld){throw 'The UE asset batch is still occupied; no import was sent.'}
        $busy=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'})
        if($busy.Count -gt 0) {
            $taskGate.ReleaseMutex();$taskHeld=$false
            Write-Output 'Waiting for the existing FPSGAME commandlet to exit; this task has not imported assets.'
            foreach($entry in $busy) {
                $existing=Get-Process -Id $entry.ProcessId -ErrorAction SilentlyContinue
                if($existing) {
                    $remaining=[Math]::Max(0,[int]($deadline-[DateTime]::UtcNow).TotalMilliseconds)
                    if(-not $existing.WaitForExit($remaining)){throw 'The existing FPSGAME commandlet has not exited; assets remain unchanged.'}
                }
            }
        }
    }
    $editor=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'}
    if($editor) {
        & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript 'D:/FPS3D/FPSGAME/SourceAssets/M870GripADS20261016/install_animations.py' -QueueWaitSeconds 600 -RequestTimeoutSeconds 600 -OutputFile ('D:/FPS3D/FPSGAME/SourceAssets/M870GripADS20261016/install_bridge_'+[guid]::NewGuid().ToString('N')+'.txt') -MaxOutputChars 2000
    } else {
        & 'D:/FPS3D/FPSGAME/Tools/ModularOutfit/Run-Authoring.ps1' -Script 'SourceAssets/M870GripADS20261016/install_animations.py' -Log 'SourceAssets/M870GripADS20261016/install_animations.log'
    }
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}