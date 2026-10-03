$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskProject='D:\FPS3D\FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    while (-not $taskHeld) {try {$taskHeld=$taskGate.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}}
    $taskEditors=Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe'" | Where-Object {$_.CommandLine -like '*FPSGAME*' -and $_.CommandLine -notmatch '(?i)(?:^|\s)-run='}
    if ($taskEditors) {throw 'Preserve running FPSGAME editor; use the existing-editor batch bridge for these saves.'}
    foreach ($taskScriptName in @('import_assets.py','install_scenes.py')) {
        $taskScript=Join-Path $PSScriptRoot $taskScriptName
        $taskLog=Join-Path $taskRoot ('Receipts/'+$taskScriptName+'.log')
        & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$taskProject\FPSGAME.uproject" '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-AllowCommandletRendering' '-d3d12' "-abslog=$taskLog" *> ($taskLog+'.stdout')
        $taskCode=$LASTEXITCODE
        Write-Output "$taskScriptName EXIT=$taskCode"
        if ($taskCode -ne 0) {throw "Background V3 save failed: $taskScriptName"}
    }
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
