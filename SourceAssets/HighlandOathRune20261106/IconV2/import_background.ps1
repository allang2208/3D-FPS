$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOut="$taskRoot/Saved/HighlandOathRune20261106/IconV2"
New-Item -ItemType Directory -Force -Path $taskOut | Out-Null
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(10))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch occupied; icon import not started.'}
    $taskOwners=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'})
    if($taskOwners.Count){throw 'Preserving running editor; use the existing bridge for this icon import.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/import_icon.py" -NullRHI -Unattended -NoSplash -NoSound -nop4 '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' "-abslog=$taskOut/import.log" *> "$taskOut/import-console.log"
    if($LASTEXITCODE -ne 0){throw "Icon import failed; see $taskOut/import.log"}
    Write-Output 'Oath V2 icon import commandlet finished.'
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
