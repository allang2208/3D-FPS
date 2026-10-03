$ErrorActionPreference='Stop'
$taskProject='D:\FPS3D\FPSGAME'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while (-not $taskHeld) {try {$taskHeld=$taskGate.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}}
    $taskActive=Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'}
    while ($taskActive) {
        if ($taskActive | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '-run='}) {throw 'Preserve running editor; use its existing bridge.'}
        Start-Sleep -Seconds 5
        $taskActive=Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'}
    }
    $taskScript=Join-Path $PSScriptRoot 'install_scenes.py'
    $taskLog=Join-Path $taskRoot 'Receipts/scenes-background.log'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$taskProject\FPSGAME.uproject" '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-nullrhi' "-abslog=$taskLog" *> ($taskLog+'.stdout')
    Write-Output "FLUE_CHEST_SAVE EXIT=$LASTEXITCODE"
    if ($LASTEXITCODE -ne 0) {throw 'Treasure save failed; preserve receipt and log.'}
} finally {if ($taskHeld) {$taskGate.ReleaseMutex()};$taskGate.Dispose()}
