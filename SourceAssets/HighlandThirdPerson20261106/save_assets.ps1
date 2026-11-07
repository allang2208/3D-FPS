$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOut="$taskRoot/Saved/HighlandThirdPerson20261106"
New-Item -ItemType Directory -Force -Path $taskOut | Out-Null
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(10))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch occupied; no asset write started.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/save_assets.py" -NullRHI -Unattended -NoSplash -NoSound -nop4 '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' "-abslog=$taskOut/save-assets.log" *> "$taskOut/save-assets-console.log"
    if($LASTEXITCODE -ne 0){throw "Asset save failed: $LASTEXITCODE"}
    Write-Output 'Highland third-person assets saved.'
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
