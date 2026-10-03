$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskProject='D:\FPS3D\FPSGAME'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskMutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    while (-not $taskHeld) {try {$taskHeld=$taskMutex.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}}
    $taskEditors=Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe'" | Where-Object {$_.CommandLine -like '*FPSGAME*' -and $_.CommandLine -notmatch '(?i)(?:^|\s)-run='}
    if ($taskEditors) {throw 'Preserve the running FPSGAME editor; background native/asset installation needs it released.'}
    foreach ($taskScriptName in @('import_assets.py','build_preview_chest.py','install_scenes.py')) {
        $taskScript=Join-Path $PSScriptRoot $taskScriptName
        $taskLog=Join-Path $taskRoot ('Receipts/'+$taskScriptName+'.log')
        & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$taskProject\FPSGAME.uproject" '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-AllowCommandletRendering' '-d3d12' "-abslog=$taskLog" *> ($taskLog+'.stdout')
        $taskCode=$LASTEXITCODE
        Write-Output "$taskScriptName EXIT=$taskCode"
        if ($taskCode -ne 0) {throw "Background workshop save failed: $taskScriptName"}
    }
} finally {
    if ($taskHeld) {$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
