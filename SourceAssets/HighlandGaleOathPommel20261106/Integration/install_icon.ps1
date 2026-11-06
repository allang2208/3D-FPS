$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskWork="$taskRoot/SourceAssets/HighlandGaleOathPommel20261106/Integration"
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    Write-Output 'Waiting for the shared UE asset window.'
    try {$taskHeld=$taskGate.WaitOne()} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME')})
    foreach($taskProcess in $taskBusy) {try {[Diagnostics.Process]::GetProcessById($taskProcess.ProcessId).WaitForExit()} catch [ArgumentException] {}}
    $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $taskEditor=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match 'FPSGAME'})
    if($taskEditor.Count) {
        & "$taskRoot/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript "$taskWork/publish_icon.py" -OutputFile "$taskWork/install-$taskStamp.txt" -MaxOutputChars 1800
        if($LASTEXITCODE -ne 0) {throw 'Editor icon import failed.'}
    } else {
        $taskLog="$taskWork/install-$taskStamp.log"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskWork/publish_icon.py" -unattended -nosplash -nosound -nullrhi -NoLiveCoding "-abslog=$taskLog" *> "$taskWork/install-$taskStamp-stdout.log"
        if($LASTEXITCODE -ne 0 -or -not (Select-String -LiteralPath $taskLog -Pattern 'GALE_OATH_FRAMED_ICON_SAVED' -Quiet)) {throw "Icon import failed: $taskLog"}
    }
    Write-Output 'GALE_OATH_FRAMED_ICON_INSTALLED'
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}