$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskScript=Join-Path $PSScriptRoot 'Scripts/install_scene.py'
$taskGui=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -and $_.CommandLine.Replace('\','/').Contains("$taskProject/FPSGAME.uproject")})
if($taskGui.Count -gt 0) {
    $taskResponse=Join-Path $PSScriptRoot ('Receipts/editor-save-'+[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')+'.json')
    & "$taskProject/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $taskScript -OutputFile $taskResponse -MaxOutputChars 1800 -RequestTimeoutSeconds 180
    exit $LASTEXITCODE
}
$taskPrior=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -and $_.CommandLine.Replace('\','/').Contains("$taskProject/FPSGAME.uproject")})
foreach($taskProcess in $taskPrior) {
    # A commandlet stalled in Live Coding startup has not loaded project code
    # or the map. Preserve it, but do not wait for assets it has not opened.
    try {
        $taskLoaded=@(([Diagnostics.Process]::GetProcessById($taskProcess.ProcessId)).Modules | Where-Object { $_.FileName.Replace('\','/').StartsWith($taskProject+'/',[StringComparison]::OrdinalIgnoreCase) })
        if($taskLoaded.Count -eq 0) { Write-Output "Project modules not loaded by PID $($taskProcess.ProcessId); preserving its startup"; continue }
    } catch [ArgumentException] { continue }
    Write-Output "Waiting for project commandlet PID $($taskProcess.ProcessId)"
    try {[Diagnostics.Process]::GetProcessById($taskProcess.ProcessId).WaitForExit()} catch [ArgumentException] {}
}
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false;$taskPrevious=$env:UE_SKIP_UBT_SDK_SETUP
try {
    try {$taskHeld=$taskMutex.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch lock unavailable; no scene changes submitted'}
    $taskGui=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -and $_.CommandLine.Replace('\','/').Contains("$taskProject/FPSGAME.uproject")})
    if($taskGui.Count -gt 0){throw 'An editor opened before saving; reroute the saved script through its batch bridge'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" '-run=pythonscript' "-script=$taskScript" '-LiveCoding=false' '-unattended' '-nop4' '-nosplash' '-nullrhi' '-nosound' "-abslog=$PSScriptRoot/Receipts/scene-save.log" *> "$PSScriptRoot/Receipts/scene-save-stdout.log"
    $taskCode=$LASTEXITCODE
    Write-Output "POWER_SCENE_SAVE_EXIT=$taskCode"
    Select-String -LiteralPath "$PSScriptRoot/Receipts/scene-save-stdout.log" -Pattern 'POWER_CONTAINER_MAP_SAVED|Error:|Traceback' | Select-Object -Last 12
    exit $taskCode
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$taskPrevious
    if($taskHeld){$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
