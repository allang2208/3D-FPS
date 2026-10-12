$ErrorActionPreference='Stop'
$root='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    $held=$gate.WaitOne([TimeSpan]::FromSeconds(60))
    if(-not $held){throw 'UE batch gate occupied.'}
    $active=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME[\\/]FPSGAME\.uproject'})
    if($active.Count){throw 'An editor/commandlet is active; no process was stopped.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$root/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -ForceHeaderGeneration "-Log=$root/Saved/BuildEditor/shotgun-models-wheel-final.log" *> "$root/Saved/BuildEditor/shotgun-models-wheel-final.stdout.log"
    if($LASTEXITCODE){throw "Editor build failed: $LASTEXITCODE"}
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
