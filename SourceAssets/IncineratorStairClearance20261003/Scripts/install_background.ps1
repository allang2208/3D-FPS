param([ValidateSet('scenes')][string]$Phase='scenes')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskProject='D:\FPS3D\FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while (-not $taskHeld) {try {$taskHeld=$taskGate.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}}
    $taskActive=Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'}
    if ($taskActive | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '-run='}) {throw 'Preserve running editor; use its bridge.'}
    while ($taskActive) {
        Start-Sleep -Seconds 5
        $taskActive=Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'}
        if ($taskActive | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '-run='}) {throw 'Preserve running editor; use its bridge.'}
    }
    $taskFile='install_scenes.py'
    $taskScript=Join-Path $PSScriptRoot $taskFile
    $taskLog=Join-Path $taskRoot "Receipts/$Phase-background.log"
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$taskProject\FPSGAME.uproject" '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-nullrhi' "-abslog=$taskLog" *> ($taskLog+'.stdout')
    Write-Output "STAIR_CLEARANCE_$Phase EXIT=$LASTEXITCODE"
    if ($LASTEXITCODE -ne 0) {throw 'Stair edit did not finish saving; preserve the authoring log.'}
} finally {if ($taskHeld) {$taskGate.ReleaseMutex()};$taskGate.Dispose()}
