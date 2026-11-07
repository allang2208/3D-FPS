$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOut="$taskRoot/Saved/HighlandThirdPersonReview20261106"
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(10))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch occupied; no capture started.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/capture.py" -NullRHI -Unattended -NoSplash -NoSound -nop4 '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' "-abslog=$taskOut/capture-v3.log" *> "$taskOut/capture-v3-console.log"
    if($LASTEXITCODE -ne 0){throw "Capture failed: $LASTEXITCODE"}
    Write-Output 'Native third-person capture complete.'
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
