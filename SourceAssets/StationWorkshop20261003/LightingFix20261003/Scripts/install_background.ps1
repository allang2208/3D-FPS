$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskProject='D:\FPS3D\FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    while (-not $taskHeld) {try {$taskHeld=$taskGate.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}}
    $taskEditors=Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME' -and $_.CommandLine -notmatch '-run='}
    if ($taskEditors) {throw 'Preserve the running editor; use the existing editor bridge.'}
    $taskScript=Join-Path $PSScriptRoot 'install_scenes.py'
    $taskLog=Join-Path $taskRoot 'Receipts/save-background.log'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$taskProject\FPSGAME.uproject" '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-AllowCommandletRendering' '-d3d12' "-abslog=$taskLog" *> ($taskLog+'.stdout')
    Write-Output "OFFICE_LIGHT_SAVE EXIT=$LASTEXITCODE"
    if ($LASTEXITCODE -ne 0) {throw 'Light save did not complete; preserve log and receipt.'}
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
