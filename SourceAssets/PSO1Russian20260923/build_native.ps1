$ErrorActionPreference='Stop'
$caseDir='D:/FPS3D/FPSGAME/SourceAssets/PSO1Russian20260923'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(900))}
    catch [Threading.AbandonedMutexException] {$held=$true; throw 'Previous UE batch ended unexpectedly; preserve state.'}
    if(-not $held){throw 'UE batch gate unavailable; no build started.'}
    $running=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        -not $_.CommandLine -or $_.CommandLine -match 'FPSGAME'
    })
    if($running.Count){throw 'FPSGAME is running; preserve the loaded module and editor state.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -WaitMutex -NoHotReloadFromIDE *> "$caseDir/build_native.log"
    $result=$LASTEXITCODE
    Get-Content -LiteralPath "$caseDir/build_native.log" -Tail 15
    exit $result
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
