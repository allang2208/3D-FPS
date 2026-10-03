$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskProject='D:\FPS3D\FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    while (-not $taskHeld) {
        try {$taskHeld=$taskGate.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    }
    $taskProcesses=Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'}
    if ($taskProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '-run='}) {
        throw 'Preserve the running editor; use the existing editor bridge.'
    }
    if ($taskProcesses) {Write-Output 'Waiting for the active background save to finish.'}
    while ($taskProcesses) {
        Start-Sleep -Seconds 5
        $taskProcesses=Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'}
        if ($taskProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '-run='}) {
            throw 'Preserve the running editor; use the existing editor bridge.'
        }
    }
    $taskScript=Join-Path $PSScriptRoot 'create_subject.py'
    $taskLog=Join-Path $taskRoot 'Receipts/save-background.log'
    New-Item -ItemType Directory -Force -Path (Split-Path $taskLog -Parent) | Out-Null
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$taskProject\FPSGAME.uproject" '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-AllowCommandletRendering' '-d3d12' "-abslog=$taskLog" *> ($taskLog+'.stdout')
    Write-Output "INCINERATOR_LINE_SAVE EXIT=$LASTEXITCODE"
    if ($LASTEXITCODE -ne 0) {throw 'Incinerator map save did not complete; preserve log and receipt.'}
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
