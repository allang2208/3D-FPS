$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    for($taskAttempt=0;$taskAttempt -lt 20 -and -not $taskHeld;$taskAttempt++) {
        try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(30))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    }
    if(-not $taskHeld){throw 'Asset batch remains busy; nothing was started.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' -run=ThunderHammerRecallAudit '-ini:Engine:[ConsoleVariables]:s.StreamableDelegateDelayFrames=0' -unattended -nop4 -nosplash -NoSound -NoLiveCoding -nullrhi -stdout -FullStdOutLogOutput ('-abslog='+$PSScriptRoot+'\runtime-engine.log') *> ($PSScriptRoot+'\runtime-console.log')
    exit $LASTEXITCODE
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
