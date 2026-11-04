$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    $held=$gate.WaitOne([TimeSpan]::FromSeconds(600))
    if(-not $held){throw 'UE batch gate is busy; no audit started.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=HatchetGripAudit "-Out=$PSScriptRoot/native-check.json" -unattended -nop4 -nosplash -NullRHI -nosound -NoShaderCompile "-abslog=$PSScriptRoot/native-check.log" *> "$PSScriptRoot/native-check-console.log"
    $code=$LASTEXITCODE
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
exit $code
