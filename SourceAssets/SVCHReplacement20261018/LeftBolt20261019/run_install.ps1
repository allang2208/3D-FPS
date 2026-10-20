$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(600))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'UE batch gate remained busy; no asset writes were sent.'}
    $editor=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'"
    if($editor){throw 'An interactive editor is running. Preserve it and use the in-editor bridge.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/install_profile.py" -unattended -nosplash -nosound -NullRHI "-abslog=$PSScriptRoot/install-final.log" *> "$PSScriptRoot/install-final-console.log"
    exit $LASTEXITCODE
} finally {
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
