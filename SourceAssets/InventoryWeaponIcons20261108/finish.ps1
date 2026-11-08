$ErrorActionPreference='Stop'
$iconProject='D:/FPS3D/FPSGAME'
& "$PSScriptRoot/produce_m249.ps1"
$iconScript=Join-Path $PSScriptRoot 'save_icons.py'
$iconStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$iconEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME' -or [string]::IsNullOrWhiteSpace($_.CommandLine)})
if($iconEditors.Count){
    & "$iconProject/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $iconScript -OutputFile "$PSScriptRoot/save-$iconStamp-response.txt" -MaxOutputChars 2500 -QueueWaitSeconds 300 -RequestTimeoutSeconds 240
    if($LASTEXITCODE -ne 0){throw 'Icon asset save did not complete in the existing editor.'}
} else {
    $iconGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$iconHeld=$false
    try {
        while(-not $iconHeld){
            try{$iconHeld=$iconGate.WaitOne(10000)}catch [Threading.AbandonedMutexException]{$iconHeld=$true}
        }
        if(@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME' -or [string]::IsNullOrWhiteSpace($_.CommandLine)}).Count){throw 'A project editor appeared; preserve it and publish through the existing bridge.'}
        $iconLog=Join-Path $PSScriptRoot "save-$iconStamp.log"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$iconProject/FPSGAME.uproject" -run=pythonscript "-script=$iconScript" -unattended -nop4 -nosplash -nosound -Multiprocess -nullrhi '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' "-abslog=$iconLog" *> "$iconLog.console.txt"
        $iconExit=$LASTEXITCODE
        if($iconExit -ne 0){throw "Icon package save failed: $iconLog"}
        Write-Output "INVENTORY_ICON_ASSETS_SAVED $iconLog"
    } finally {if($iconHeld){$iconGate.ReleaseMutex()};$iconGate.Dispose()}
}
