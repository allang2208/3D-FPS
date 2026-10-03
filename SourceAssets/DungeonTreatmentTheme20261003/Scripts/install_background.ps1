$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskProject='D:\FPS3D\FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while (-not $taskHeld) {try {$taskHeld=$taskGate.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}}
    $taskActive=Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'}
    if ($taskActive | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '-run='}) {throw 'Preserve the running editor; use its existing bridge.'}
    while ($taskActive) {
        Start-Sleep -Seconds 5
        $taskActive=Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'}
        if ($taskActive | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '-run='}) {throw 'Preserve the running editor; use its existing bridge.'}
    }
    $taskLog=Join-Path $taskRoot 'Receipts/install-background.log'
    New-Item -ItemType Directory -Force -Path (Split-Path $taskLog -Parent) | Out-Null
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$taskProject\FPSGAME.uproject" '-run=pythonscript' "-script=$PSScriptRoot/install_theme.py" '-unattended' '-nop4' '-nosplash' '-nosound' '-nullrhi' "-abslog=$taskLog" *> ($taskLog+'.stdout')
    Write-Output "TREATMENT_THEME EXIT=$LASTEXITCODE"
    if ($LASTEXITCODE -ne 0) {throw 'Theme save did not complete; preserve the receipt and log.'}
} finally {if ($taskHeld) {$taskGate.ReleaseMutex()};$taskGate.Dispose()}
