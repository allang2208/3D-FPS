$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    while($true) {
        try {$taskHeld=$taskGate.WaitOne(15000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
        if(-not $taskHeld){continue}
        $taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'})
        if($taskEditors | Where-Object Name -eq 'UnrealEditor.exe'){throw 'FPSGAME editor is open; background native build deferred, loaded binaries preserved.'}
        $taskBuilds=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='cl.exe'" | Where-Object {$_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool'})
        if($taskEditors.Count -eq 0 -and $taskBuilds.Count -eq 0){break}
        $taskGate.ReleaseMutex();$taskHeld=$false;Start-Sleep -Seconds 15
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -MaxParallelActions=4 -WaitMutex "-Log=$taskRoot/SourceAssets/RSH12Grip20261003/build_editor_03.log"
    if($LASTEXITCODE -ne 0){throw 'RSH-12 native build failed; see build_editor_03.log'}
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
