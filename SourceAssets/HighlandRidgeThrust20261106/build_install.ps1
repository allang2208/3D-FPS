$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOutput="$taskRoot/Saved/RidgeThrustTuning20261106"
[IO.Directory]::CreateDirectory($taskOutput) | Out-Null
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    Write-Output 'Waiting for the shared UE build/import window.'
    try {$taskHeld=$taskGate.WaitOne()} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    $taskBuilders=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe'})
    foreach($taskBuilder in $taskBuilders) {
        try {[Diagnostics.Process]::GetProcessById($taskBuilder.ProcessId).WaitForExit()} catch [ArgumentException] {}
    }
    $taskEditor=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'})
    if($taskEditor.Count) {throw 'Preserving the existing editor; use its bridge for asset installation and native hot update.'}
    $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $taskBuildLog="$taskOutput/build-editor-$taskStamp.log"
    Write-Output "RIDGE_BUILD_START $taskBuildLog"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -NoHotReloadFromIDE -MaxParallelActions=4 *> $taskBuildLog
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;log=$taskBuildLog;runtime_tested=$false;editor_launched=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskOutput/build-receipt.json" -Encoding utf8
    Get-Content -LiteralPath $taskBuildLog -Tail 14 | Where-Object {$_ -notlike '[[]Adaptive Build[]]*'}
    if($taskExit -ne 0) {throw "Editor build failed: $taskBuildLog"}
    $taskImportLog="$taskOutput/publish-$taskStamp.log"
    Write-Output "RIDGE_IMPORT_START $taskImportLog"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskRoot/SourceAssets/HighlandRidgeThrust20261105/publish_gather.py" -unattended -nosplash -nosound -nullrhi -NoLiveCoding "-abslog=$taskImportLog" *> "$taskOutput/publish-$taskStamp-stdout.log"
    $taskExit=$LASTEXITCODE
    $taskSaved=($taskExit -eq 0) -and (Select-String -LiteralPath $taskImportLog -Pattern 'RIDGE_GATHER_SAVED' -Quiet)
    @{exit_code=$taskExit;material_saved=$taskSaved;log=$taskImportLog;runtime_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskOutput/install-receipt.json" -Encoding utf8
    if(-not $taskSaved) {throw "Gather material not saved: $taskImportLog"}
    Write-Output 'RIDGE_TUNING_COMPILED_AND_SAVED'
} finally {
    if($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}