$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(30))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'Animation save queue timed out'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/AssetHost/AssetHost.uproject" -run=pythonscript "-script=$taskRoot/install_assets.py" -unattended -nosplash -NullRHI -NoSound -NoP4 -UTF8Output "-abslog=$taskRoot/isolated-save.log" *> "$taskRoot/isolated-save-console.log"
    if($LASTEXITCODE -ne 0){throw "Isolated save failed: $LASTEXITCODE"}
    $taskDeadline=(Get-Date).AddMinutes(5)
    while(Get-Process UnrealEditor-Cmd -ErrorAction SilentlyContinue) {
        if((Get-Date) -gt $taskDeadline){throw 'Another commandlet is active; staged assets preserved'}
        Start-Sleep -Seconds 5
    }
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'An editor is now running; staged assets preserved for in-editor publication'}
    & py -3.11 -X utf8 "$taskRoot/publish_isolated.py"
    if($LASTEXITCODE -ne 0){throw 'Animation publication failed'}
    & py -3.11 -X utf8 "$taskRoot/finalize.py"
    if($LASTEXITCODE -ne 0){throw 'Delivery receipt not saved'}
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}