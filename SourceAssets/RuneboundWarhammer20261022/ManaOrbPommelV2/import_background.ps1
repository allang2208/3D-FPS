$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(600))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'Asset batch still busy; preserve current work.'}
    if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'"){throw 'Editor running: preserve its loaded packages; use the existing bridge.'}
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' -run=pythonscript ('-script='+$PSScriptRoot+'\import_assets.py') -unattended -nop4 -nosplash -NoSound -NoLiveCoding -RenderOffscreen -stdout -FullStdOutLogOutput ('-abslog='+$PSScriptRoot+'\import.log') *> ($PSScriptRoot+'\import-console.log')
    exit $LASTEXITCODE
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
