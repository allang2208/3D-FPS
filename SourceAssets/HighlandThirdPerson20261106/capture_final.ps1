$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOut="$taskRoot/Saved/HighlandThirdPerson20261106"
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(10))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch occupied; no capture started.'}
    $env:HIGHLAND_REVIEW_OUTPUT="$taskOut/NativeFinal"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskRoot/Tools/HighlandThirdPersonReview20261106/capture.py" -NullRHI -Unattended -NoSplash -NoSound -nop4 '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' "-abslog=$taskOut/capture-final.log" *> "$taskOut/capture-final-console.log"
    if($LASTEXITCODE -ne 0){throw "Capture failed: $LASTEXITCODE"}
    Write-Output 'Installed Highland native graph capture complete.'
} finally {
    Remove-Item Env:HIGHLAND_REVIEW_OUTPUT -ErrorAction SilentlyContinue
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
