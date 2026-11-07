param([string]$ScriptName='install.py')
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskScript=Join-Path $PSScriptRoot $ScriptName
$taskStem=[IO.Path]::GetFileNameWithoutExtension($ScriptName)
$taskOut="$taskRoot/Saved/HighlandBroadbladeGuardFinish20261106"
New-Item -ItemType Directory -Force -Path $taskOut | Out-Null
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch occupied; asset operation not started.'}
    $taskOwners=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'})
    if($taskOwners.Count){throw 'Preserving running editor; use the existing bridge.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskScript" -NullRHI -Unattended -NoSplash -NoSound -nop4 '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' "-abslog=$taskOut/$taskStem.log" *> "$taskOut/$taskStem-console.log"
    if($LASTEXITCODE -ne 0){throw "Asset operation failed; see $taskOut/$taskStem.log"}
    Write-Output "Broadblade asset operation finished: $taskStem"
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
