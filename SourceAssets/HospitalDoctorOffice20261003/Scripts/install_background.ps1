param([ValidateSet('assets','scenes')][string]$Phase='assets')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskProject='D:\FPS3D\FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while (-not $taskHeld) {try {$taskHeld=$taskGate.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}}
    while (Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME'}) {Start-Sleep -Seconds 5}
    if (Get-CimInstance Win32_Process | Where-Object {($_.Name -in @('UnrealEditor.exe','FPSGAME.exe')) -and $_.CommandLine -match 'FPSGAME'}) {throw 'Preserve the active editor/game; save through its bridge.'}
    $taskScript=Join-Path $PSScriptRoot $(if ($Phase -eq 'assets') {'import_assets.py'} else {'install_scenes.py'})
    $taskLog=Join-Path $taskRoot "Receipts/$Phase-background.log"
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$taskProject\FPSGAME.uproject" '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-AllowCommandletRendering' '-d3d12' "-abslog=$taskLog" *> ($taskLog+'.stdout')
    Write-Output "HOSPITAL_OFFICE_$Phase EXIT=$LASTEXITCODE"
    if ($LASTEXITCODE -ne 0) {throw 'Hospital office save failed; preserve logs and receipt.'}
} finally {if ($taskHeld) {$taskGate.ReleaseMutex()};$taskGate.Dispose()}
