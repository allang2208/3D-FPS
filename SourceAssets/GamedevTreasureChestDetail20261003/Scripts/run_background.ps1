param([ValidateSet('Author','Install')][string]$Stage='Author')
$ErrorActionPreference='Stop'
$taskProject='D:\FPS3D\FPSGAME'
$taskRoot=Split-Path $PSScriptRoot -Parent
if ($Stage -eq 'Author') {
    & 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --python-exit-code 1 --python "$PSScriptRoot\author_chest.py" *> "$taskRoot\Receipts\blender.log"
    if ($LASTEXITCODE -ne 0) {throw 'Chest authoring failed; preserve log.'}
    & 'C:\Users\allan\AppData\Local\Programs\Python\Python311\python.exe' "$PSScriptRoot\make_surface_maps.py" *> "$taskRoot\Receipts\textures.log"
    if ($LASTEXITCODE -ne 0) {throw 'Chest PBR authoring failed; preserve log.'}
    Write-Output 'TREASURE_AUTHOR_COMPLETE'
    exit
}
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while (-not $taskHeld) {try {$taskHeld=$taskGate.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}}
    $taskActive=Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'}
    while ($taskActive) {
        if ($taskActive | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '-run='}) {throw 'Preserve running editor; use its existing bridge with install_detail.py.'}
        Start-Sleep -Seconds 5
        $taskActive=Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'}
    }
    $taskScript=Join-Path $PSScriptRoot 'install_detail.py'
    $taskLog=Join-Path $taskRoot 'Receipts/install-engine.log'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$taskProject\FPSGAME.uproject" '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-nullrhi' "-abslog=$taskLog" *> ($taskLog+'.stdout')
    Write-Output "TREASURE_DETAIL_INSTALL EXIT=$LASTEXITCODE"
    if ($LASTEXITCODE -ne 0) {throw 'Chest install failed; preserve receipt and log.'}
} finally {if ($taskHeld) {$taskGate.ReleaseMutex()};$taskGate.Dispose()}
