$ErrorActionPreference = 'Stop'
$taskRoot = 'D:\FPS3D\FPSGAME\SourceAssets\KukriDashHands20261028'
$taskProject = 'D:\FPS3D\FPSGAME\FPSGAME.uproject'
$taskBuild = 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'

# Wait for the already running build process, without taking the engine build lock.
$taskBuilds = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -in @('dotnet.exe', 'UnrealBuildTool.exe') -and $_.CommandLine -match 'UnrealBuildTool'
})
foreach ($taskExisting in $taskBuilds) {
    $taskProcess = Get-Process -Id $taskExisting.ProcessId -ErrorAction SilentlyContinue
    if ($taskProcess) {
        Write-Output "Waiting for existing build process $($taskExisting.ProcessId)."
        while (-not $taskProcess.WaitForExit(45000)) {
            Write-Output "Existing build process $($taskExisting.ProcessId) is still running."
        }
    }
}

$taskBlockers = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -in @('UnrealEditor.exe', 'UnrealEditor-Cmd.exe', 'FPSGAME.exe') -or
    ($_.Name -in @('dotnet.exe', 'UnrealBuildTool.exe') -and $_.CommandLine -match 'UnrealBuildTool')
})
if ($taskBlockers.Count) {
    $taskBlockers | Select-Object ProcessId,Name,CommandLine | Format-List
    throw 'Editor or another build is active; leaving processes unchanged.'
}

$taskStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$taskLog = Join-Path $taskRoot "editor-build-resume-$taskStamp.log"
$taskConsole = Join-Path $taskRoot "editor-build-resume-console-$taskStamp.log"
$taskSource = 'D:\FPS3D\FPSGAME\Source\FPSGAME\Characters\FPSBodyKukriMotion.h'
$taskSourceHash = (Get-FileHash -LiteralPath $taskSource -Algorithm SHA256).Hash
Write-Output "Starting FPSGAMEEditor build; log: $taskLog"
& $taskBuild FPSGAMEEditor Win64 Development "-Project=$taskProject" -NoHotReload -NoHotReloadFromIDE "-Log=$taskLog" 2>&1 | Tee-Object -FilePath $taskConsole
$taskCode = $LASTEXITCODE
[ordered]@{
    target = 'FPSGAMEEditor Win64 Development'
    exit_code = $taskCode
    completed = (Get-Date -Format o)
    log = $taskLog
    console_log = $taskConsole
    animation_source = $taskSource
    animation_source_sha256_at_build_start = $taskSourceHash
    runtime_tested = $false
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskRoot 'editor-build-resume-result.json') -Encoding utf8
exit $taskCode
