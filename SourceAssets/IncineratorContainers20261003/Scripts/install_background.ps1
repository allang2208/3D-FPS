param([ValidateSet('assets','capture','scenes')][string]$Phase='assets')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskProject='D:\FPS3D\FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    while (-not $taskHeld) {try {$taskHeld=$taskGate.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}}
    $taskActive=Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'}
    if ($taskActive | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '-run='}) {
        throw 'Preserve the running editor; use the existing editor bridge.'
    }
    if ($taskActive) {Write-Output 'Waiting for the active background save to finish.'}
    while ($taskActive) {
        Start-Sleep -Seconds 5
        $taskActive=Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'}
        if ($taskActive | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '-run='}) {
            throw 'Preserve the running editor; use the existing editor bridge.'
        }
    }
    $taskFile=@{assets='import_assets.py';capture='capture_placement_source.py';scenes='install_scenes.py'}[$Phase]
    $taskScript=Join-Path $PSScriptRoot $taskFile
    $taskLog=Join-Path $taskRoot "Receipts/$Phase-background.log"
    New-Item -ItemType Directory -Force -Path (Split-Path $taskLog -Parent) | Out-Null
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$taskProject\FPSGAME.uproject" '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-AllowCommandletRendering' '-d3d12' "-abslog=$taskLog" *> ($taskLog+'.stdout')
    Write-Output "TREATMENT_CONTAINERS_$Phase EXIT=$LASTEXITCODE"
    if ($LASTEXITCODE -ne 0) {throw 'Treatment container assets did not finish saving; preserve log and receipt.'}
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
