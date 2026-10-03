param([switch]$StationLineOnly)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskProject='D:\FPS3D\FPSGAME'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskMutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if (-not $taskHeld) {Write-Output 'Waiting for the current UE batch.'}
    while (-not $taskHeld) {try {$taskHeld=$taskMutex.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}}
    $taskEditors=Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe'" | Where-Object {$_.CommandLine -like '*FPSGAME*' -and $_.CommandLine -notmatch '(?i)(?:^|\s)-game(?:\s|$)|(?:^|\s)-run='}
    if ($taskEditors) {throw 'Preserve the running editor; production save requires existing MCP handling.'}
    $taskScripts=if ($StationLineOnly) {@('create_station_line_subject.py')} else {@('install_production.py','create_station_line_subject.py')}
    foreach ($taskScriptName in $taskScripts) {
        $taskScript=Join-Path $PSScriptRoot $taskScriptName
        $taskLog=Join-Path $taskRoot ('Receipts/'+$taskScriptName+'.log')
        & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$taskProject\FPSGAME.uproject" '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-AllowCommandletRendering' '-d3d12' "-abslog=$taskLog" *> ($taskLog+'.stdout')
        $taskCode=$LASTEXITCODE
        Write-Output "$taskScriptName EXIT=$taskCode"
        if ($taskCode -ne 0) {throw "Background save failed: $taskScriptName"}
    }
    if (-not $StationLineOnly) {
        & py -3.11 (Join-Path $PSScriptRoot 'retire_subjects.py')
        if ($LASTEXITCODE -ne 0) {throw 'Staff sample retirement remains incomplete.'}
    }
} finally {
    if ($taskHeld) {$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
