param()
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskProject='D:\FPS3D\FPSGAME'
$taskBatch='E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskReport=@{editor_exit=$null;game_exit=$null;tests_run=$false;rendered=$false;editor_started=$false;logs=@{}}
try {
    do {
        $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*'})
        if ($taskBusy.Count -gt 0) {Start-Sleep -Seconds 10}
    } while ($taskBusy.Count -gt 0)
    try {$taskHeld=$taskMutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    while (-not $taskHeld) {try {$taskHeld=$taskMutex.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}}
    $taskEditors=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -like '*FPSGAME*'})
    if ($taskEditors.Count -gt 0) {throw 'Preserve the open editor; native build requires its DLLs to be released.'}
    foreach ($taskTarget in @('FPSGAMEEditor','FPSGAME')) {
        $taskKind=if ($taskTarget -eq 'FPSGAMEEditor') {'editor'} else {'game'}
        $taskLog=Join-Path $taskRoot ('Receipts/build-'+$taskKind+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
        $taskReport.logs[$taskKind]=$taskLog
        & $taskBatch $taskTarget Win64 Development "-Project=$taskProject\FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE "-Log=$taskLog"
        $taskReport[($taskKind+'_exit')]=$LASTEXITCODE
        if ($LASTEXITCODE -ne 0) {throw "$taskKind build failed; see $taskLog"}
    }
} finally {
    [IO.File]::WriteAllText((Join-Path $taskRoot 'Receipts/native-build.json'),($taskReport | ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
    if ($taskHeld) {$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}