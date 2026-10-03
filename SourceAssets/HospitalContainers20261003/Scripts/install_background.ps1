param([ValidateSet('assets','scenes')][string]$Phase='assets')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskProject='D:\FPS3D\FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    while (-not $taskHeld) {try {$taskHeld=$taskGate.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}}
    $taskActive=Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe' OR Name = 'FPSGAME.exe' OR Name = 'UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME'}
    if ($taskActive) {throw 'Preserve the active project process; use the existing editor bridge when appropriate.'}
    $taskScript=Join-Path $PSScriptRoot $(if ($Phase -eq 'assets') {'import_assets.py'} else {'install_scenes.py'})
    $taskLog=Join-Path $taskRoot "Receipts/$Phase-background.log"
    New-Item -ItemType Directory -Force -Path (Split-Path $taskLog -Parent) | Out-Null
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$taskProject\FPSGAME.uproject" '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-AllowCommandletRendering' '-d3d12' "-abslog=$taskLog" *> ($taskLog+'.stdout')
    Write-Output "HOSPITAL_CONTAINERS_$Phase EXIT=$LASTEXITCODE"
    if ($LASTEXITCODE -ne 0) {throw 'Hospital container save did not complete; preserve log and receipt.'}
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
